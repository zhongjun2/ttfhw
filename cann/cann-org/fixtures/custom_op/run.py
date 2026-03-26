import ctypes, os, numpy as np

lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "add_custom.so"))
lib.AddCustom.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64
]
lib.AddCustom.restype = ctypes.c_uint32

n = 8
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
scalar = np.array([10.0], dtype=np.float32)
y = np.zeros(n, dtype=np.float32)

ret = lib.AddCustom(
    x.ctypes.data_as(ctypes.c_void_p),
    scalar.ctypes.data_as(ctypes.c_void_p),
    y.ctypes.data_as(ctypes.c_void_p),
    ctypes.c_int64(n)
)
assert ret == 0, f"Kernel returned error code {ret}"
print(",".join(f"{v:.1f}" for v in y))
