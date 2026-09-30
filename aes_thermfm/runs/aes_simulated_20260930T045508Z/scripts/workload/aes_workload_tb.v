`timescale 1ns/1ps
module aes_workload_tb;
  reg clk=0;
  always #1 clk=~clk;
  reg rst=0, ld=0;
  reg [127:0] key=128'h000102030405060708090a0b0c0d0e0f;
  reg [127:0] text_in=0;
  wire done;
  wire [127:0] text_out;
  aes_cipher_top dut(.clk(clk),.rst(rst),.ld(ld),.done(done),.key(key),.text_in(text_in),.text_out(text_out));
  reg [127:0] plaintext[0:271], ciphertext[0:271];
  integer i, gap, cycles;
  reg [2047:0] dump_path;
  time start_time;
  task encrypt;
    input integer idx;
    begin
      @(negedge clk); text_in=plaintext[idx]; ld=1;
      @(negedge clk); ld=0;
      cycles=0;
      while(done !== 1'b1 && cycles<40) begin @(negedge clk); cycles=cycles+1; end
      if(done !== 1'b1) $fatal(1,"Timeout at block %0d",idx);
      if(text_out !== ciphertext[idx]) $fatal(1,"Cipher mismatch block %0d got=%h expected=%h",idx,text_out,ciphertext[idx]);
    end
  endtask
  initial begin
    if(!$value$plusargs("GAP=%d",gap)) gap=0;
    if(!$value$plusargs("VCD=%s",dump_path)) $fatal(1,"Missing VCD path");
    $readmemh("/work/inputs/workload/plaintext.hex",plaintext);
    $readmemh("/work/inputs/workload/ciphertext.hex",ciphertext);
    repeat(4) @(negedge clk);
    rst=1;
    for(i=0;i<16;i=i+1) encrypt(i);
    @(negedge clk);
    start_time=$time;
    $dumpfile(dump_path); $dumpvars(0,dut);
    for(i=16;i<272;i=i+1) begin encrypt(i); repeat(gap) @(negedge clk); end
    $display("PASS blocks=272 warmup=16 measured=256 gap_cycles=%0d start_ps=%0t end_ps=%0t duration_ps=%0t",gap,start_time,$time,$time-start_time);
    $finish;
  end
  initial begin #100000; $fatal(1,"Global timeout"); end
endmodule
