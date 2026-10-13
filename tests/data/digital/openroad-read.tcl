read_db $::env(DIGITAL_RUN_DIR)/smoke.odb
set block [ord::get_db_block]
if {[$block getName] != "smoke" || [llength [$block getInsts]] != 1 || [llength [$block getNets]] != 2} {
  error "Database round-trip failed"
}
puts "OPENROAD_DATABASE_PASS instances=1 nets=2"
