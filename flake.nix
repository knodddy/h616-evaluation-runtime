{
  description = "H616 bare-metal development and TF boot tooling";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      forEachSystem = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
      ];
    in
    {
      formatter = forEachSystem (system: nixpkgs.legacyPackages.${system}.nixfmt);

      devShells = forEachSystem (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          cross = pkgs.pkgsCross.aarch64-embedded;
        in
        {
          default = pkgs.mkShell {
            CROSS_COMPILE = cross.stdenv.cc.targetPrefix;
            # Host hardening defaults are unsuitable for freestanding firmware.
            hardeningDisable = [ "all" ];

            packages = with pkgs; [
              # Target tools run on the host; mkShell retains its native compiler.
              cross.stdenv.cc
              cross.buildPackages.binutils
              cross.buildPackages.gdb

              # Host build tools for the payload, TF-A, and U-Boot.
              git
              gnumake
              pkg-config
              bison
              flex
              swig
              bc
              which
              perl

              # Source formatting, static analysis, and editor support.
              clang-tools
              nixfmt

              # Device trees and firmware image packaging.
              dtc
              ubootTools
              # Required by upstream U-Boot's image builder.
              (python3.withPackages (ps: [
                ps.setuptools
                ps.pyelftools
                ps.libfdt
              ]))

              # TF image preparation and inspection.
              genimage
              dosfstools
              mtools
              util-linux
              coreutils
              file

              # UART console/transfers and optional USB FEL boot.
              picocom
              lrzsz
              sunxi-tools
              usbutils
            ];

            buildInputs = with pkgs; [
              openssl
              ncurses
            ];
          };
        }
      );
    };
}
