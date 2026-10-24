# Startup trace 50: panic prefix and clock rejection

24 October 2026. [Trace 49](gpu-startup-trace-49-result.md) proves a panic before
RAM userspace and `-EINVAL` returns from both engine module initializations;
it does not establish their causal relationship.

Patch 0099 adds diagnostic detail only. The separate
`wingray_gpu_panic_trace_defconfig` uses cookie `0x584d0050`. It preserves the
same DT, reservations, clocks, reset policy and startup-only RAM service.
**No rendering, voltage change or speculative engine workaround is enabled.**

The existing panic notifier stores at most the first 20 bytes of `panic()`'s
formatted message in previously unused record bytes `0x6c–0x7f`, then publishes
the panic flag. It handles a NULL message or an early NUL without reading past
the NUL. The record and readback remain exactly 128 bytes using the same tested
reader/mapping. Cookie 49 retains its old offset bound and reserved-word checks;
cookie 50 alone permits these last five words.

Per-engine clock stages are `0x100 + clock_index*16 + event`:
event 0 acquisition entry; 1 acquisition error; 2 old reported rate; 3 rounded
requested rate; 4 invalid rounded rate; 5 zero old rate despite a positive
rounded rate. Results hold the associated error/rate. The module and client
outer error returns preserve the inner failure stage. Host and non-diagnostic
behavior are unchanged; the trace does not relax rate checks or alter rates.

Full ARM build, actual cookie-50 reset-instruction tests, C bounds/writer/panic
copy tests and decoder tests pass. The clock fixtures now check the retained
codes for acquisition errors, rounding errors and zero old rates. Existing
cleanup/failure fixtures and the packed startup-only image checks pass. Sources
match the committed kernel and compiled output; the DT remains byte-identical
to attempt 48. These checks are not physical acceptance.

Local candidate: `artifacts/gpu-startup50-ready/wingray-gpu-render-diagnostic.img`,
5,883,904 bytes, SHA256
`91b7a5ed87ac30e9f43777868bd096b746a6cdac7fdd435d6c5afc5e9b8440bb`.
Build with `XOOM_PROFILE=gpu-panic-trace`; package using `--startup-trace
--trace-cookie 0x584d0050` and fresh directories. Use the same boot-only test,
original restoration/full hash verification and one guarded snapshot sequence.
