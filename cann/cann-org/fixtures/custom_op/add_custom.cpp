#include "cpu_kernel_utils.h"
#include <vector>
#include <stdint.h>

extern "C" __attribute__((visibility("default")))
uint32_t AddCustom(void* x, void* scalar, void* y, int64_t n) {
    float* in = static_cast<float*>(x);
    float s = *static_cast<float*>(scalar);
    float* out = static_cast<float*>(y);
    for (int64_t i = 0; i < n; ++i) {
        out[i] = in[i] + s;
    }
    return 0;
}
