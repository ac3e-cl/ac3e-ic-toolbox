module counter(input wire clk, input wire rst, output reg [3:0] count);
always @(posedge clk) begin
    if (rst) count <= 4'b0;
    else count <= count + 1'b1;
end
endmodule
