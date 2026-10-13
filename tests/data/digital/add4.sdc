create_clock -name virtual_clk -period 10
set_input_delay 1 -clock virtual_clk [all_inputs]
set_output_delay 1 -clock virtual_clk [all_outputs]
