# Running Nextflow pipelines from a notebook

Both Day 1 afternoon sessions launch an nf-core-style pipeline. This page collects what you
need to get that working, and what to do when a Google Colab runtime will not cooperate.

## The three ingredients

| | Why | How |
|---|---|---|
| **Java 17+** | Nextflow runs on the JVM | `apt-get install -y openjdk-17-jdk-headless` |
| **Nextflow** | the workflow engine | `curl -s https://get.nextflow.io \| bash` |
| **A container engine** | every pipeline step runs in a container with pinned software | Docker, or Singularity/Apptainer |

```python
!apt-get -qq update > /dev/null
!apt-get -qq install -y openjdk-17-jdk-headless > /dev/null
!wget -qO- https://get.nextflow.io | bash
!mv -f nextflow /usr/local/bin/nextflow && chmod +x /usr/local/bin/nextflow
!nextflow -v
```

## Choosing a container engine

| Engine | Where it works | Profile |
|---|---|---|
| **Docker** | your laptop, a workstation, a cloud VM | `-profile docker` |
| **Singularity / Apptainer** | HPC clusters, and the best bet in Colab | `-profile singularity` or `-profile apptainer` |
| **Conda** | metaboigniter only — **not** quantmsdiann | `-profile conda` |

Colab has **no Docker daemon**, so Docker is not an option there. Apptainer can be installed:

```python
!apt-get -qq install -y software-properties-common > /dev/null
!add-apt-repository -y ppa:apptainer/ppa > /dev/null 2>&1
!apt-get -qq update > /dev/null
!apt-get -qq install -y apptainer > /dev/null
```

Both notebooks include a detection cell that picks whatever is available and sets
`CONTAINER_PROFILE` accordingly.

### ⚠️ When it does not work

Container support in Colab depends on the runtime you happen to be given, and Apptainer
sometimes fails there for reasons outside anyone's control. **This is not your mistake.**

If the pipeline will not start:

1. Keep going. Both notebooks are written so that everything after the pipeline section works
   without it — they load the study's real processed output instead. You lose the experience
   of watching a pipeline run, not the content of the session.
2. Try the same commands later on a machine with Docker. They are unchanged.
3. For metabolomics only, try Conda:

   ```python
   !pip install -q condacolab
   import condacolab; condacolab.install()   # this restarts the kernel
   ```

   After the restart, re-run the setup cells (skipping the `condacolab.install()` line) and
   use `-profile conda`. Conda resolution is slower and less reproducible than containers, so
   prefer containers when you have them.

## Anatomy of a Nextflow command

```bash
nextflow run bigbio/quantmsdiann -r v2.3.0 -profile test_dia_dotd,docker --outdir results -resume
```

| Part | Meaning |
|---|---|
| `nextflow run <org>/<repo>` | fetch and run the pipeline straight from GitHub |
| `-r v2.3.0` | pin the **version**. Always do this in a real project — an unpinned pipeline is an unreproducible one |
| `-profile a,b` | bundles of preset configuration; comma-separated, order matters when they overlap |
| `--outdir` | **single dash** = Nextflow's own option, **double dash** = a pipeline parameter |
| `-resume` | reuse every step that completed successfully in a previous run |
| `-c my.config` | extra configuration — for **resources only**, never for parameters |

## Disk, memory and time

Nextflow writes two things:

- **`work/`** — one hashed directory per task. This is what `-resume` reads, and it grows
  fast. Delete it when you are finished with a run, or when you run out of disk.
- **`--outdir`** — the tidy, published results.

Cap resources with a config file:

```groovy
process {
    resourceLimits = [ cpus: 4, memory: '12.GB', time: '6.h' ]
}
```

On Colab that matters: a free runtime typically offers 2 vCPU and ~12 GB RAM, and asking a
process for 16 CPUs makes it queue forever rather than fail with a clear message.

On a cluster, share the container cache between users and runs:

```bash
export NXF_SINGULARITY_CACHEDIR=/shared/singularity_cache
```

## Reading the log

Nextflow prints one line per process as it completes:

```
[a1/3f9c2b] process > BIGBIO_QUANTMSDIANN:...:DIANN_PRELIMINARY (Con1) [100%] 1 of 1 ✔
```

The hash is the `work/` subdirectory. When a step fails, go there and read `.command.err` and
`.command.log` — the real error is almost always in one of those, not in the Nextflow output.

```bash
cd work/a1/3f9c2b*/ && cat .command.err
```

Other useful commands:

```bash
nextflow log                 # past runs
nextflow log <run> -f status,workdir,name   # per-task detail
nextflow clean -f -before <run>             # free disk from older runs
nextflow pull bigbio/quantmsdiann -r v2.3.0  # refresh a cached pipeline
```

## Further reading

- Nextflow documentation: <https://www.nextflow.io/docs/latest/>
- nf-core installation guide: <https://nf-co.re/docs/usage/installation>
- nf-core troubleshooting: <https://nf-co.re/docs/usage/troubleshooting>
- The nf-core Slack is friendly and fast: <https://nf-co.re/join/slack>
