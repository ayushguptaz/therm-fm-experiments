set activity $::env(WORKLOAD)
# Run with the pinned ORFS OpenROAD binary after completing the AES flow.
set base /work/flow/results/nangate45/aes/base
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $base/6_final.odb
read_sdc $base/6_final.sdc
source $platform/setRC.tcl
if {[file exists $base/6_final.spef]} {
    read_spef $base/6_final.spef
    set parasitic_source extracted_spef
} else {
    estimate_parasitics -placement
    set parasitic_source placement_estimate
}
report_units
report_checks -path_delay max -group_path_count 3 > /work/outputs/timing.rpt
write_def /work/outputs/aes.def
write_verilog /work/outputs/aes_mapped.v
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
set core [$block getCoreArea]
set f [open /work/outputs/geometry.json w]
puts $f "\{"
puts $f [format {"dbu_per_micron": %d, "die_um": [%g,%g,%g,%g], "core_um": [%g,%g,%g,%g], "parasitics": "%s"} $dbu \
    [expr {[$die xMin]/double($dbu)}] [expr {[$die yMin]/double($dbu)}] [expr {[$die xMax]/double($dbu)}] [expr {[$die yMax]/double($dbu)}] \
    [expr {[$core xMin]/double($dbu)}] [expr {[$core yMin]/double($dbu)}] [expr {[$core xMax]/double($dbu)}] [expr {[$core yMax]/double($dbu)}] $parasitic_source]
puts $f "\}"
close $f
if {[llength [info commands sta::cmd_scene]]} {
    set scene [sta::cmd_scene]
} else {
    set scene [sta::cmd_corner]
}
read_vcd -scope aes_workload_tb/dut /work/outputs/workload/${activity}.vcd
report_activity_annotation > /work/outputs/activity_${activity}.rpt
report_activity_annotation -report_unannotated > /work/outputs/activity_unannotated_${activity}.rpt
report_checks -path_delay max -group_path_count 3 > /work/outputs/timing.rpt
report_power -digits 8 > /work/outputs/power_${activity}.rpt
    set design_p [sta::design_power $scene]
    set f [open /work/outputs/cells_${activity}.csv w]
    puts $f "name,master,x0_um,y0_um,x1_um,y1_um,internal_W,switching_W,leakage_W,total_W"
    set count 0
    set total 0.0
    foreach inst [get_cells -hierarchical *] {
        set dbinst [sta::sta_to_db_inst $inst]
        if {$dbinst == "NULL"} {continue}
        set name [$dbinst getName]
        if {[string first , $name] >= 0} {error "Unexpected comma in instance name"}
        set master [[$dbinst getMaster] getName]
        set box [$dbinst getBBox]
        lassign [sta::instance_power $inst $scene] internal switching leakage power
        puts $f [join [list $name $master \
            [expr {[$box xMin]/double($dbu)}] [expr {[$box yMin]/double($dbu)}] \
            [expr {[$box xMax]/double($dbu)}] [expr {[$box yMax]/double($dbu)}] \
            $internal $switching $leakage $power] ,]
        incr count
        set total [expr {$total+$power}]
    }
    close $f
    set f [open /work/outputs/power_summary_${activity}.txt w]
    puts $f "power_source=gate_level_vcd"
    puts $f "workload=$activity"
    puts $f "activity_annotation=simulation_vcd"
    puts $f "exported_cells=$count"
    puts $f "db_instances=[llength [$block getInsts]]"
    puts $f "sum_cell_power_W=$total"
    puts $f "design_power_components_W=$design_p"
    close $f
    puts "POWER_EXPORT activity=$activity cells=$count total_W=$total design_components=$design_p"
