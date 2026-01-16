{
  description = "A minimal Python devshell without external dependencies";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      allSystems = [
        "x86_64-linux" # 64-bit Intel/AMD Linux
        "aarch64-linux" # 64-bit ARM Linux
        "x86_64-darwin" # Intel macOS
        "aarch64-darwin" # Apple Silicon macOS
      ];
      forAllSystems = nixpkgs.lib.genAttrs allSystems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config = {
              allowUnfree = true;
            };
          };
        in
        {
          default =
            pkgs.mkShell rec {
              shellPkgs = with pkgs; [
                (python3.withPackages (python-pkgs: with python-pkgs; [
                  pip
                  virtualenv
                  requests
                  numpy
                ]))
                nodejs # For WebUI frontend (npm/npx)
                poppler-utils # For Vibe Code PDF Processing
                glib
                libglvnd
                zlib
              ];

              nativeBuildInputs = with pkgs; [ glib ];

              packages = [
                shellPkgs
              ];

              LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath shellPkgs}:${pkgs.stdenv.cc.cc.lib.outPath}/lib:$LD_LIBRARY_PATH";

              shellHook = ''
                echo "🐍 Python DevShell activated"
                echo "Python version: $(python --version)"
                export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${pkgs.glib}/lib"
              '';
              env = {
              };
            };
          }
        );
      apps = forAllSystems (system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config = {
              allowUnfree = true;
            };
          };
          trainScript = pkgs.writeShellScript "train-cubalibre-long" ''
            exec ${pkgs.fish}/bin/fish ${./scripts/train_cubalibre_long.fish} "$@"
          '';
        in
        {
          train-cubalibre-long = {
            type = "app";
            program = "${trainScript}";
          };
        }
      );
    };
}
