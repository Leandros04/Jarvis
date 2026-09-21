import sys
from pathlib import Path


def normalize(version):
    raw = version.strip().lstrip("vV")
    parts = raw.split(".")
    nums = []
    for part in parts[:4]:
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits or 0))
    while len(nums) < 4:
        nums.append(0)
    return raw, nums


if len(sys.argv) != 3:
    raise SystemExit("usage: make_version_info.py <version> <output>")

version, nums = normalize(sys.argv[1])
out = Path(sys.argv[2])
out.parent.mkdir(parents=True, exist_ok=True)

content = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({nums[0]}, {nums[1]}, {nums[2]}, {nums[3]}),
    prodvers=({nums[0]}, {nums[1]}, {nums[2]}, {nums[3]}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [
          StringStruct(u'CompanyName', u'JARVIS Project'),
          StringStruct(u'FileDescription', u'JARVIS personal assistant'),
          StringStruct(u'FileVersion', u'{version}'),
          StringStruct(u'InternalName', u'JARVIS'),
          StringStruct(u'OriginalFilename', u'JARVIS.exe'),
          StringStruct(u'ProductName', u'JARVIS for Windows'),
          StringStruct(u'ProductVersion', u'{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
out.write_text(content, encoding="utf-8")
print(out)
