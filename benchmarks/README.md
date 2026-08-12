# RTX 5090 benchmark protocol

This directory defines the benchmark; it does not contain invented results.

1. Fill every environment field in `rtx5090.json` on the machine under test.
2. Use the same prompt, inputs, seed, dimensions, frame count, and output format.
3. Run one warmup plus three measured runs per workflow and variant.
4. Keep the first Triton compilation time separate from warm end-to-end time.
5. Record peak VRAM externally with `nvidia-smi` until the runner can source it
   reliably from the same process.
6. Review matching frames for identity, motion, audio, and visible artifacts.
7. Publish the generated JSON and Markdown only after the run completes.

```bash
axon-creative benchmark --suite benchmarks/rtx5090.json
```
