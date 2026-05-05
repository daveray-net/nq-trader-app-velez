#!/bin/bash
# run the container...
###
#  -e HSA_XNACK=1 \

### podman command...
podman run -it --rm \
  --device=/dev/kfd --device=/dev/dri \
  --group-add 39 --group-add 105 \
  --privileged=true \
  --security-opt seccomp=unconfined \
  --ipc=host \
  --cap-add=SYS_PTRACE \
  -v $(pwd):/app:Z \
  -v ./data:/app/data:Z \
  -v ./data/.triton/cache:/app/triton_cache:Z \
  -e TRITON_CACHE_DIR=/app/triton_cache \
  -e HF_HOME=/app/data/.hf_cache \
  -e HSA_ENABLE_SDMA=0 \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.0 \
  -e PYTORCH_ROCM_ARCH=gfx900 \
  -e HSA_IOMMU_SUPPORT=1 \
  -e shm_size="2gb" \
  rocm-pytorch:latest

 ### compose command...
# podman-compose up -d && podman attach rocm-pytorch-vm

