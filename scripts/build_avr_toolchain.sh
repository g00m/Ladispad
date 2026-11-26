#!/usr/bin/env bash
#
# Build a native (Apple Silicon) AVR GCC toolchain for Ladispad firmware builds.
#
# Why: Homebrew removed the avr-gcc formula, and the prebuilt macOS AVR
# toolchains (PlatformIO / Microchip / Arduino) are x86_64-only, which needs
# Rosetta 2. This builds binutils + gcc + avr-libc from source instead, so the
# QMK build runs natively with no emulation.
#
# Usage:  ./scripts/build_avr_toolchain.sh [--jobs N]
# Result: $HOME/Development/avr-toolchain/bin/avr-gcc
#
set -euo pipefail

JOBS="$(sysctl -n hw.ncpu 2>/dev/null || echo 4)"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --jobs) JOBS="$2"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

PREFIX="${AVR_TOOLCHAIN_PREFIX:-$HOME/Development/avr-toolchain}"
WORK="${AVR_TOOLCHAIN_WORK:-$HOME/Development/avr-toolchain-src}"

BINUTILS_VERSION="2.44"
GCC_VERSION="14.2.0"
AVR_LIBC_VERSION="2.3.2"

BINUTILS_URL="https://ftp.gnu.org/gnu/binutils/binutils-${BINUTILS_VERSION}.tar.xz"
GCC_URL="https://ftp.gnu.org/gnu/gcc/gcc-${GCC_VERSION}/gcc-${GCC_VERSION}.tar.xz"
AVR_LIBC_URL="https://github.com/avrdudes/avr-libc/releases/download/avr-libc-2_3_2-release/avr-libc-${AVR_LIBC_VERSION}.tar.bz2"

echo "== Ladispad AVR toolchain build"
echo "   prefix : $PREFIX"
echo "   work   : $WORK"
echo "   jobs   : $JOBS"

mkdir -p "$WORK/src" "$WORK/build"
cd "$WORK/src"

fetch() {  # fetch <url> <file>
    [[ -f "$2" ]] || { echo "-- downloading $2"; curl -fL --retry 3 -o "$2" "$1"; }
}
fetch "$BINUTILS_URL" "binutils-${BINUTILS_VERSION}.tar.xz"
fetch "$GCC_URL" "gcc-${GCC_VERSION}.tar.xz"
fetch "$AVR_LIBC_URL" "avr-libc-${AVR_LIBC_VERSION}.tar.bz2"

extract() {  # extract <file>
    local dir="${1%.tar.*}"
    [[ -d "$dir" ]] || { echo "-- extracting $1"; tar xf "$1"; }
}
extract "binutils-${BINUTILS_VERSION}.tar.xz"
extract "gcc-${GCC_VERSION}.tar.xz"
extract "avr-libc-${AVR_LIBC_VERSION}.tar.bz2"

echo "-- binutils"
mkdir -p "$WORK/build/binutils-$BINUTILS_VERSION" && cd "$WORK/build/binutils-$BINUTILS_VERSION"
"$WORK/src/binutils-${BINUTILS_VERSION}/configure" \
    --target=avr --prefix="$PREFIX" --disable-nls --disable-werror --disable-gdb \
    --with-system-zlib
make -j"$JOBS"
make install
export PATH="$PREFIX/bin:$PATH"

echo "-- gcc (bootstrap, C/C++ for avr)"
cd "$WORK/src/gcc-${GCC_VERSION}" && ./contrib/download_prerequisites
mkdir -p "$WORK/build/gcc-$GCC_VERSION" && cd "$WORK/build/gcc-$GCC_VERSION"
"$WORK/src/gcc-${GCC_VERSION}/configure" \
    --target=avr --prefix="$PREFIX" \
    --disable-nls --disable-libssp --disable-libada --disable-libgomp \
    --disable-libmudflap --disable-libstdcxx-pch \
    --with-dwarf2 --enable-languages=c,c++
make -j"$JOBS"
make install

echo "-- avr-libc"
mkdir -p "$WORK/build/avr-libc-$AVR_LIBC_VERSION" && cd "$WORK/build/avr-libc-$AVR_LIBC_VERSION"
"$WORK/src/avr-libc-${AVR_LIBC_VERSION}/configure" --host=avr --prefix="$PREFIX"
make -j"$JOBS"
make install

echo "-- smoke test"
echo '#include <avr/io.h>
int main(void){ DDRB = 0xFF; return 0; }' > "$WORK/smoke.c"
"$PREFIX/bin/avr-gcc" -mmcu=atmega32u4 -Os -o "$WORK/smoke.elf" "$WORK/smoke.c"
"$PREFIX/bin/avr-size" "$WORK/smoke.elf"
echo "== done: $PREFIX/bin/avr-gcc"
