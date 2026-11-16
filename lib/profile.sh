# shellcheck shell=bash
# lib/profile.sh: Go profiles from the Weaviate pods (only with --profile).
#
# Captures the same profiles, in the same order, as Weaviate support's own
# profiling tools, so support can read them the usual way:
#
#   pods/<pod>/profiles/heap.pb.gz        instant profiles
#   pods/<pod>/profiles/allocs.pb.gz
#   pods/<pod>/profiles/mutex.pb.gz
#   pods/<pod>/profiles/goroutine.pb.gz
#   pods/<pod>/profiles/goroutine_dump.txt  every goroutine with its stack (?debug=2)
#   pods/<pod>/profiles/cpu.pb.gz         PROFILE_DURATION seconds, then
#   pods/<pod>/profiles/fgprof.pb.gz      PROFILE_DURATION seconds (never together)
#
# One pod at a time, through one temporary port-forward to Weaviate's debug
# port (GO_PROFILING_PORT, default 6060). Only the GET paths allowed in
# lib/guard.sh are called on that port. Profiles hold function names, file
# paths and counters from the Weaviate binary; Weaviate sets no profile
# labels, so they hold no tenant names or data.

PROFILE_INSTANT="heap allocs mutex goroutine"
PROFILE_TIMED="cpu fgprof"
PROFILE_DOWNLOAD_TIMEOUT=600   # ceiling for instant profiles; big heaps take minutes
PROFILE_TIMED_OVERHEAD=30      # cpu/fgprof may take duration + this

# Debug port of the Weaviate container, and whether it is switched off.
profile_port() {
  local p; p=$(sts_env GO_PROFILING_PORT)
  case "$p" in ''|*[!0-9]*) printf '6060' ;; *) printf '%s' "$p" ;; esac
}
profile_listener_disabled() {
  case "$(sts_env GO_PROFILING_DISABLE)" in [Tt]rue|1|[Oo]n|[Yy]es) return 0 ;; esac
  return 1
}

# Path on the debug port for one profile.
_profile_path() {
  case "$1" in
    cpu)    printf '/debug/pprof/profile?seconds=%s' "$PROFILE_DURATION" ;;
    fgprof) printf '/debug/fgprof?seconds=%s&ignore=gopark&ignore=GoWrapper' "$PROFILE_DURATION" ;;
    dump)   printf '/debug/pprof/goroutine?debug=2' ;;
    *)      printf '/debug/pprof/%s' "$1" ;;
  esac
}

# Preflight: can we reach the debug port, and does it serve requests?
# Sets PF_PROFILE to ok | off | forbidden | unavailable, and PROFILE_ERROR.
probe_profiling() {
  PF_PROFILE="off"; PROFILE_ERROR=""
  [ "${PROFILE:-0}" = 1 ] || return 0
  PROFILE_PORT=$(profile_port)
  local pod="${SEL_WEAVIATE_PODS%% *}"
  if [ -z "$pod" ]; then PF_PROFILE="unavailable"; PROFILE_ERROR="no Weaviate pod selected"; return 0; fi
  if profile_listener_disabled; then
    PF_PROFILE="unavailable"; PROFILE_ERROR="GO_PROFILING_DISABLE is set, so Weaviate has no debug port"; return 0
  fi
  tunnel_open "$pod" "$PROFILE_PORT"
  case $? in
    0) ;;
    11) PF_PROFILE="forbidden"; PROFILE_ERROR="port-forward not allowed"; return 0 ;;
    *)  PF_PROFILE="unavailable"; PROFILE_ERROR="debug port $PROFILE_PORT not reachable: $TUNNEL_ERROR"; return 0 ;;
  esac
  local code
  code=$(http_get_profile "http://127.0.0.1:$TUNNEL_PORTS" "/debug/pprof/" "$RAW/pprof-index.html" 30)
  tunnel_close "$TUNNEL_PID"
  case "$code" in
    200) PF_PROFILE="ok" ;;
    404) PF_PROFILE="unavailable"; PROFILE_ERROR="debug endpoints are off (set DEBUG_ENDPOINTS_ENABLED=true to allow profiling)" ;;
    000) PF_PROFILE="unavailable"; PROFILE_ERROR="debug port $PROFILE_PORT did not answer" ;;
    *)   PF_PROFILE="unavailable"; PROFILE_ERROR="HTTP $code from the debug port" ;;
  esac
  return 0
}

# Seconds a pod takes: two timed profiles, plus a little for the rest.
profile_seconds_per_pod() { echo $(( 2 * PROFILE_DURATION + 10 )); }

# fetch one profile into dir; prints nothing, returns 0 ok, 13 not served, 1 failed.
_profile_fetch() {
  local base="$1" name="$2" dir="$3" file max code
  if [ "$name" = dump ]; then file="$dir/goroutine_dump.txt"; else file="$dir/$name.pb.gz"; fi
  case " $PROFILE_TIMED " in
    *" $name "*) max=$((PROFILE_DURATION + PROFILE_TIMED_OVERHEAD)) ;;
    *)           max=$PROFILE_DOWNLOAD_TIMEOUT ;;
  esac
  code=$(http_get_profile "$base" "$(_profile_path "$name")" "$file.part" "$max")
  if [ "$code" != 200 ] || [ ! -s "$file.part" ]; then
    rm -f "$file.part"; log_line WARN "profile $name: HTTP ${code:-none}"
    [ "$code" = 404 ] && return 13
    return 1
  fi
  # A cut-off download must never look like a good profile.
  if [ "$name" != dump ] && ! gzip -t "$file.part" 2> /dev/null; then
    rm -f "$file.part"; log_line WARN "profile $name: incomplete download, removed"
    return 1
  fi
  mv "$file.part" "$file"
}

# "heap dump cpu" -> "heap, goroutine dump, cpu"
_profile_names() { printf '%s' "$1" | sed 's/ /, /g; s/dump/goroutine dump/'; }

_profile_pod() {
  local pod="$1" dir="$STAGE/pods/$1/profiles" base name rc got="" failed=""
  tunnel_open "$pod" "$PROFILE_PORT"
  case $? in
    0) ;;
    11) step_detail "port-forward not allowed"; return 11 ;;
    *)  step_detail "debug port not reachable: $TUNNEL_ERROR"; return 13 ;;
  esac
  base="http://127.0.0.1:$TUNNEL_PORTS"
  mkdir -p "$dir"
  # Same order as support's tools: instant profiles, goroutine dump, then
  # cpu and fgprof one after the other (together, each shows up in the other).
  for name in $PROFILE_INSTANT dump $PROFILE_TIMED; do
    [ "$name" = cpu ] && info "$pod: CPU profile, then fgprof (${PROFILE_DURATION}s each)..."
    _profile_fetch "$base" "$name" "$dir"; rc=$?
    if [ "$rc" -eq 0 ]; then got="$got $name"; else failed="$failed $name"; fi
    if [ "$rc" -eq 13 ] && [ -z "$got" ]; then break; fi   # debug endpoints off: stop early
  done
  tunnel_close "$TUNNEL_PID"
  rmdir "$dir" 2> /dev/null
  got="${got# }"; failed="${failed# }"
  if [ -z "$got" ]; then
    case "$rc" in
      13) step_detail "debug endpoints are off (DEBUG_ENDPOINTS_ENABLED)"; return 13 ;;
      *)  step_detail "no profile could be downloaded${failed:+ ($failed)}"; return 1 ;;
    esac
  fi
  step_detail "$(_profile_names "$got")${failed:+; failed: $(_profile_names "$failed")}"
  return 0
}

collect_profiles() {
  heading "Profiles (one pod at a time, ${PROFILE_DURATION}s CPU + ${PROFILE_DURATION}s fgprof each)"
  if [ "$PF_PROFILE" != "ok" ]; then
    local st=13; [ "$PF_PROFILE" = "forbidden" ] && st=11
    _noprofile() { step_detail "${PROFILE_ERROR:-not available}"; return "$st"; }
    run_step profile "profiles" _noprofile
    return
  fi
  local p
  for p in $SEL_WEAVIATE_PODS; do
    run_step profile "$p" _profile_pod "$p"
  done
}
