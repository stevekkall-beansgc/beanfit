from beanfit.profile import DeviceProfile

M5_MAX_128 = DeviceProfile(
    os="macos", arch="apple_silicon", backend="unified",
    chip="Apple M5 Max", family="M5", variant="Max",
    ram_gib=128.0, metal_cap_gib=96.0, model_budget_gib=96.0,
    mem_bandwidth_gbs=600.0, bw_source="estimate",
)

M4_PRO_48 = DeviceProfile(
    os="macos", arch="apple_silicon", backend="unified",
    chip="Apple M4 Pro", family="M4", variant="Pro",
    ram_gib=48.0, metal_cap_gib=36.0, model_budget_gib=36.0,
    mem_bandwidth_gbs=273.0, bw_source="spec_sheet",
)

M2_BASE_8 = DeviceProfile(  # smallest plausible: nothing fits the catalog
    os="macos", arch="apple_silicon", backend="unified",
    chip="Apple M2", family="M2", variant="",
    ram_gib=8.0, metal_cap_gib=6.0, model_budget_gib=4.0,
    mem_bandwidth_gbs=100.0, bw_source="spec_sheet",
)

INTEL_MAC_16 = DeviceProfile(
    os="macos", arch="other", backend="unknown",
    chip="Intel(R) Core(TM) i9", family="", variant="",
    ram_gib=16.0, metal_cap_gib=12.0, model_budget_gib=12.0,
    mem_bandwidth_gbs=60.0, bw_source="unknown_fallback",
)
