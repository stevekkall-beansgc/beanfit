# Physical text release hold — October25,2026

On the owned iPhone14ProMax/iOS26.6.1, Pocket2 passed its20-check resource packet, but its quality packet stopped on a real thermal event after12 summaries. The host driver was interrupted; the same run was recovered from the phone. The one-second samples missed the brief hot state, so that raw report still says thermal_gate:true; completed:false and automatic_pass:false remain failures. The guarded real thermal event and failure are the acceptance disposition, not the stale sampled boolean.

Pocket3 used one CPU thread. Its resource run began at fair temperature and stopped hot; it is not a cooled-baseline test. A later quality run began nominal and stopped at serious temperature after4 cases. Both are failures. Their latched highest_real_thermal_state is2 and thermal_gate:false. No frozen packet, latency, memory or heat limit was relaxed. Twelve/four correct automated phrase screens do not establish full quality acceptance.

The single-thread experiment did not establish a thermal improvement and is not adopted as a release fix. Current source retains the adaptive2-nominal/1-fair policy, plus the reporting fix that retains brief real thermal events and excludes deliberate injections. Native app distribution is blocked. The next candidate requires lower-power runtime/model engineering and a new full acceptance run. No TestFlight/App Store upload, native tag or model qualification occurred.

All retained cases are synthetic. These are app-process reports, not independent review, battery endurance or whole-system Instruments evidence. The original four-case interruption from October22 remains separately unproven.
