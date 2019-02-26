FROM pytorch/pytorch:1.0-cuda10.0-cudnn7-devel

#-----------------------------------------------------
# Build CMake
RUN curl -L -O https://github.com/Kitware/CMake/releases/download/v3.12.4/cmake-3.12.4.tar.gz && \
    tar -xvzf cmake-3.12.4.tar.gz && \
    rm cmake-3.12.4.tar.gz && \
    cd cmake-3.12.4 && \
    ./bootstrap && make && make install

#-----------------------------------------------------
# ISPC: Embree dependency
# https://github.com/ispc/ispc/blob/master/docker/ubuntu/Dockerfile

# Packages required to build ISPC and Clang.
RUN apt-get -y update && apt-get install -y wget build-essential vim gcc g++ git subversion python m4 bison flex zlib1g-dev ncurses-dev libtinfo-dev libc6-dev-i386 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local/src

# Fork ispc on github and clone *your* fork.
RUN cd /usr/local/src && git clone https://github.com/ispc/ispc.git

# This is home for Clang builds
RUN mkdir /usr/local/src/llvm

ENV ISPC_HOME=/usr/local/src/ispc
ENV LLVM_HOME=/usr/local/src/llvm

# If you are going to run test for future platforms, go to
# http://www.intel.com/software/sde and download the latest version,
# extract it, add to path and set SDE_HOME.

WORKDIR /usr/local/src/ispc

# Build Clang with all required patches.
# Pass required LLVM_VERSION with --build-arg LLVM_VERSION=<version>.
# By default 5.0 is used.
# Note self-build options, it's required to build clang and ispc with the same compiler,
# i.e. if clang was built by gcc, you may need to use gcc to build ispc (i.e. run "make gcc"),
# or better do clang selfbuild and use it for ispc build as well (i.e. just "make").
# "rm" are just to keep docker image small.
ARG LLVM_VERSION=5.0
RUN ./alloy.py -b --version=$LLVM_VERSION --selfbuild --git && \
    rm -rf $LLVM_HOME/build-$LLVM_VERSION $LLVM_HOME/llvm-$LLVM_VERSION $LLVM_HOME/bin-$LLVM_VERSION_temp $LLVM_HOME/build-$LLVM_VERSION_temp

ENV PATH=$LLVM_HOME/bin-$LLVM_VERSION/bin:$PATH

# Configure ISPC build
RUN mkdir build_$LLVM_VERSION
WORKDIR build_$LLVM_VERSION
RUN cmake ../ -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_INSTALL_PREFIX=/usr/local/src/ispc/bin-$LLVM_VERSION

# Build ISPC
RUN make ispc -j8 && make install
WORKDIR ../
RUN rm -rf build_$LLVM_VERSION


#-----------------------------------------------------
# Build Redner

RUN conda install --yes pybind11 numpy scikit-image
RUN apt-get update && apt-get install -y \
    libtbb-dev \ 
    pkg-config \ 
    libglfw3-dev \
    libopenexr-dev \ 
    libopenimageio-dev \
    ranger

# Upgrade to gcc 7
# https://gist.github.com/jlblancoc/99521194aba975286c80f93e47966dc5
RUN apt-get install -y software-properties-common && \
    add-apt-repository ppa:ubuntu-toolchain-r/test && \
    apt update && \
    apt install g++-7 -y && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 60 \
                         --slave /usr/bin/g++ g++ /usr/bin/g++-7 && \
    update-alternatives --config gcc

#RUN wget https://github.com/embree/embree/releases/download/v3.2.4/embree-3.2.4.x86_64.linux.tar.gz
#WORKDIR /
#RUN git clone --recursive https://github.com/supershinyeyes/redner.git 
COPY . /app
WORKDIR /app
RUN chmod -R a+w /app
ARG OPTIX_VERSION=6.0.0
RUN mv dependencies/NVIDIA-OptiX-SDK-${OPTIX_VERSION}-linux64 /usr/local/optix
ENV LD_LIBRARY_PATH /usr/local/optix/lib64:${LD_LIBRARY_PATH}

# Build Redner
RUN mkdir build && \
    cd build && \
    cmake .. && \
    make install -j 8 

# WORKDIR /redner
# RUN chmod -R a+w /redner

# python -c "import torch; print(torch.cuda.is_available())"
# python -c "import pyredner"


# CMake Error at cmake/FindOptiX.cmake:82 (message):
#   optix library not found.  Please locate before proceeding.
# Call Stack (most recent call first):
#   cmake/FindOptiX.cmake:91 (OptiX_report_error)
#   CMakeLists.txt:15 (find_package)

#  OpenImageIO not found in your environment. You can 1) install
#                               via your OS package manager, or 2) install it
#                               somewhere on your machine and point OPENIMAGEIO_ROOT to it. (missing: OPENIMAGEIO_INCLUDE_DIR OPENIMAGEIO_LIBRARY) 

# export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda-10.0/lib64
# docker run --runtime=nvidia -it --rm --env="DISPLAY" shinyeyes/redner:v0.4 /bin/bash 