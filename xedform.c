// Decode hex byte strings on stdin (one per line), print XED iclass and iform.
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "xed/xed-interface.h"

int main(int argc, char** argv) {
    xed_tables_init();
    xed_state_t state;
    xed_decoded_inst_t xedd;
    xed_state_init2(&state, XED_MACHINE_MODE_LONG_64, XED_ADDRESS_WIDTH_64b);
    char line[256];
    unsigned char buf[32];
    while (fgets(line, sizeof(line), stdin)) {
        char* p = line;
        int n = 0;
        unsigned v;
        while (n < (int)sizeof(buf) && sscanf(p, "%2x", &v) == 1) {
            buf[n++] = (unsigned char)v;
            p += 2;
        }
        xed_decoded_inst_zero_set_mode(&xedd, &state);
        xed_error_enum_t err = xed_decode(&xedd, buf, n);
        if (err != XED_ERROR_NONE) {
            printf("DECODE_ERROR %s -\n", xed_error_enum_t2str(err));
        } else {
            printf("OK %s %s eosz=%d easz=%d regs=",
                   xed_iclass_enum_t2str(xed_decoded_inst_get_iclass(&xedd)),
                   xed_iform_enum_t2str(xed_decoded_inst_get_iform_enum(&xedd)),
                   xed_operand_values_get_effective_operand_width(&xedd),
                   xed_operand_values_get_effective_address_width(&xedd));
            for (int i = XED_OPERAND_REG0; i <= XED_OPERAND_REG3; i++) {
                xed_reg_enum_t r = xed_decoded_inst_get_reg(&xedd, (xed_operand_enum_t)i);
                printf("%s%s", i > XED_OPERAND_REG0 ? "," : "",
                       xed_reg_enum_t2str(r));
            }
            printf(" imm=%lld base=%s idx=%s scale=%d displen=%u zero=%d\n",
                   (long long)xed_decoded_inst_get_signed_immediate(&xedd),
                   xed_reg_enum_t2str(xed_decoded_inst_get_base_reg(&xedd, 0)),
                   xed_reg_enum_t2str(xed_decoded_inst_get_index_reg(&xedd, 0)),
                   xed_decoded_inst_get_scale(&xedd, 0),
                   xed_decoded_inst_get_memory_displacement_width(&xedd, 0),
                   xed_decoded_inst_zeroing(&xedd));
        }
    }
    return 0;
}
