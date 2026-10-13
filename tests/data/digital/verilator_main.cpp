#include "Vadd4.h"
#include "verilated.h"
#include <iostream>
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vadd4 dut;
    for (unsigned a = 0; a < 16; ++a) {
        for (unsigned b = 0; b < 16; ++b) {
            dut.a = a; dut.b = b; dut.eval();
            if (dut.y != a + b) {
                std::cerr << "sum mismatch a=" << a << " b=" << b
                          << " y=" << unsigned(dut.y) << "\n";
                return 1;
            }
        }
    }
    dut.final();
    std::cout << "SIMULATION_PASS vectors=256\n";
    return 0;
}
