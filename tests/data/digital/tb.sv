`timescale 1ns/1ps
module tb;
  reg [3:0] a, b;
  wire [4:0] y;
  integer i, j;
  add4 dut (.a(a), .b(b), .y(y));
  initial begin
    for (i=0; i<16; i=i+1) begin
      for (j=0; j<16; j=j+1) begin
        a = i[3:0]; b = j[3:0]; #1;
        if (y !== (i+j)) $fatal(1, "sum mismatch a=%0d b=%0d y=%0d", i,j,y);
      end
    end
    $display("SIMULATION_PASS vectors=256");
    $finish;
  end
endmodule
