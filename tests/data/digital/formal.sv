module formal_top(input [3:0] a, input [3:0] b);
  wire [4:0] y;
  add4 dut (.a(a), .b(b), .y(y));
  always @* begin
    assert (y >= {1'b0,a});
    assert (y >= {1'b0,b});
    assert (y - {1'b0,b} == {1'b0,a});
  end
endmodule
