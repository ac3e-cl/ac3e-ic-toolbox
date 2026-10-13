module add4(input [3:0] a, input [3:0] b, output [4:0] y);
  assign y = {1'b0, a} + {1'b0, b};
endmodule
