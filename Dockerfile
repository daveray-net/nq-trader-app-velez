FROM registry.access.redhat.com/ubi9/ubi-minimal:latest

LABEL maintainer="daveray@daveray.net"
LABEL description="Minimal ROCm PyTorch environment for ROCm/GPU - AMD Radeon Vega 8 Graphics"

ENV SMDEV_CONTAINER_OFF=1

COPY requirements.txt .
# 3. Add the ROCm 6.4 Repository for RHEL 9
# Using the specific 6.4 branch to match your Fedora 43 host
# Note pytorch is using ROCm5.7 to match the LENOVO Thinkpad A485 hardware gfx900
RUN printf "[ROCm-6.4]\n\
name=ROCm 6.4\n\
baseurl=https://repo.radeon.com/rocm/el9/6.4/main\n\
enabled=1\n\
priority=50\n\
gpgcheck=1\n\
gpgkey=https://repo.radeon.com/rocm/rocm.gpg.key" > /etc/yum.repos.d/rocm.repo \
    && microdnf install -y \
    python3.12 \
    python3.12-pip \
    shadow-utils \
    tar \
    gzip \
    which \
    elfutils-libelf \
    numactl-libs \
    pciutils-libs \
    rocm-core \
    hip-runtime-amd \
    rocm-hip-libraries \
    rocminfo \
    && rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm \
    && ln -sf /usr/bin/python3.12 /usr/bin/python \
    && ln -sf /usr/bin/pip3.12 /usr/bin/pip \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.7 --break-system-packages \
    && pip install -r requirements.txt \
    && microdnf clean all

# 4. Set Environment Variables
ENV PATH="/opt/rocm/bin:/opt/rocm/llvm/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/rocm/lib:/usr/local/lib:${LD_LIBRARY_PATH}"

# IMPORTANT: APU Support Override
# Most APUs need to "spoof" a supported GPU architecture (like gfx900)
# to allow the ROCm runtime to initialize.
ENV HSA_ENABLE_SDMA=0
ENV HSA_OVERRIDE_GFX_VERSION=9.0.0
ENV PYTORCH_ROCM_ARCH=gfx900
ENV HSA_IOMMU_SUPPORT=1
ENV SHM_SIZE=2gb

WORKDIR /workspace
CMD ["/usr/bin/bash" ]

