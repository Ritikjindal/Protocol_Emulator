module uart_tx (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,   // request: send the byte on `data`
    input  wire [7:0] data,
    output wire       tx,
    output wire       busy
);
    localparam CYCLES_PER_BIT = 434;

    // the four registers from the table
    reg       busy_r;
    reg [8:0] cyc_cnt;   // 0..433  -> 9 bits
    reg [3:0] bit_cnt;   // 0..9    -> 4 bits
    reg [7:0] shreg;     // the byte snapshot
    reg start_meta;
    reg start_sync;


    // the two "events" from the table's columns
    wire go       = start_sync && !busy_r;                              // start pulse, guarded
    wire slot_end = busy_r && (cyc_cnt == CYCLES_PER_BIT - 1);     // counter at 433
    wire frame_end = slot_end && (bit_cnt == 9);

    always @(posedge clk) begin
        if (!rst_n)
            cyc_cnt <= 0;
        else if (go || slot_end)
            cyc_cnt <= 0;
        else if (busy_r)
            cyc_cnt <= cyc_cnt + 1'b1;
    end

    always @(posedge clk) begin
        if (!rst_n)
            bit_cnt <= 0;
        else if (slot_end) begin
            if (bit_cnt != 9)
                bit_cnt <= bit_cnt+1'b1;
            else
                bit_cnt <= 0;
        end     
    end

    always @(posedge clk) begin
        if (!rst_n)
            busy_r <= 0;
        else if (frame_end)
            busy_r <= 0;
        else if (go)
            busy_r <= 1;
    end 

    always @(posedge clk) begin
        if (!rst_n)
            shreg <= 0;
        else if (go)
            shreg <= data;
        else if (bit_cnt>=1 && bit_cnt<=8 && slot_end)
            shreg <= shreg >> 1;
    end

    always@(posedge clk) begin
        if (!rst_n) begin
            start_meta<=0;
            start_sync<=0;
        end
        else begin
            start_meta <= start;
            start_sync <= start_meta;
        end
    end 

    assign tx = (!busy_r) ? 1'b1: ((bit_cnt==0)? 1'b0: ((bit_cnt==9)? 1'b1: shreg[0]));
    assign busy = busy_r;
endmodule