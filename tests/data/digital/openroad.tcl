set platform $::env(DIGITAL_PLATFORM_DIR)
set output $::env(DIGITAL_RUN_DIR)
read_lef $platform/lef/NangateOpenCellLibrary.tech.lef
read_lef $platform/lef/NangateOpenCellLibrary.macro.lef
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_verilog $::env(DIGITAL_DATA_DIR)/openroad.v
link_design smoke
set block [ord::get_db_block]
if {[llength [$block getInsts]] != 1 || [llength [$block getNets]] != 2} {
  error "Unexpected linked design instance/net counts"
}
write_db $output/smoke.odb
write_def $output/smoke.def
