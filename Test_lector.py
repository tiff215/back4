# list_readers.py
from smartcard.System import readers

r = readers()
print("Lectores detectados:", r)
for i, reader in enumerate(r):
    print(i, "->", reader)
