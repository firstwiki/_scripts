
abspath() {
  # $1 : relative filename
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}

REPOS="firstwiki.github.io frc0000 frc1000 frc2000 frc3000 frc4000 frc5000 frc6000"
ALL_REPOS="_common $REPOS"
