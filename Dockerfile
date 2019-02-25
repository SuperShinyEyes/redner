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
# cmake -D CUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda-10.0 ..
# cmake -D CUDA_LIBRARIES
# THRUST_INCLUDE_DIR
# optix_prime_LIBRARY
# CUDA_curand_LIBRARY

#-----------------------------------------------------
# WORKDIR /
#RUN git clone --recursive https://github.com/supershinyeyes/redner.git 
COPY . /app
RUN chmod -R a+wx /app
WORKDIR /app

ARG OPTIX_VERSION=6.0.0
COPY dependencies/NVIDIA-OptiX-SDK-${OPTIX_VERSION}-linux64 /usr/local/optix
ENV LD_LIBRARY_PATH /usr/local/optix/lib64:${LD_LIBRARY_PATH}

RUN cmake -DOptiX_INCLUDE=/usr/local/optix/include -Doptix_LIBRARY=/usr/local/optix/lib64 -Doptix_prime_LIBRARY=/usr/local/optix/SDK

RUN mkdir build && \
    cd build && \
    cmake .. && \
    make install -j 8 

# WORKDIR /redner
# RUN chmod -R a+w /redner

# python -c "import torch; print(torch.cuda.is_available())"

# CMake Error at cmake/FindOptiX.cmake:82 (message):
#   optix library not found.  Please locate before proceeding.
# Call Stack (most recent call first):
#   cmake/FindOptiX.cmake:91 (OptiX_report_error)
#   CMakeLists.txt:15 (find_package)
