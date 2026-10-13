module add4(input [3:0] a, input [3:0] b, output [4:0] y);
  wire [4:0] carry;
  assign carry[0] = 1'b0;
  genvar i;
  generate for (i=0; i<4; i=i+1) begin : bit_adder
    assign y[i] = a[i] ^ b[i] ^ carry[i];
    assign carry[i+1] = (a[i] & b[i]) | (a[i] & carry[i]) | (b[i] & carry[i]);
  end endgenerate
  assign y[4] = carry[4];
endmodule
