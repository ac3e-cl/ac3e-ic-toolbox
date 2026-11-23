#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
unset LD_LIBRARY_PATH GNUCAP_PLUGPATH
for executable in gnucap gnucap-conf gnucap-mg-vams modelgen-verilog; do
    require_command "$executable"
    [[ $(command -v "$executable") == "/usr/local/bin/$executable" ]] || fail "$executable not in /usr/local/bin"
done
for lookup in --includedir --libdir --pkglibdir; do
    directory=$(gnucap-conf "$lookup")
    [[ $directory == /usr/local/* && -d $directory ]] || fail "gnucap-conf $lookup points to invalid directory: $directory"
done

work="$TEST_ROOT/run/analog/gnucap-modelgen-verilog"
mkdir -p "$work"
cd "$work"
cat > resistor.va <<'EOF'
`include "disciplines.vams"
module toolbox_resistor(p, n);
inout p, n;
electrical p, n;
analog I(p, n) <+ V(p, n) / 1000.0;
endmodule
EOF
modelgen-verilog -I"$(gnucap-conf --includedir)" --cc resistor.va > resistor.cc
# Compile the generated source against the headers shipped with Gnucap.
read -r -a cppflags <<< "$(gnucap-conf --cppflags)"
c++ "${cppflags[@]}" -fPIC -shared resistor.cc -o resistor.so
printf 'quit\n' > quit.ckt
gnucap -a ./resistor.so -b quit.ckt > gnucap.log 2>&1
if grep -Eiq 'error|undefined symbol|cannot (load|open)' gnucap.log; then
    fail "Gnucap could not load the generated model: $work/gnucap.log"
fi
pass 'Gnucap generated, compiled and loaded a Verilog-A resistor model'
