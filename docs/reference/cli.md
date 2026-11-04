# Command line

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

The `coalitionkit` command comes with the package.

## `coalitionkit`

```text
usage: coalitionkit [-h] {up,conform,pack,server} ...

positional arguments:
  {up,conform,pack,server}
    up                  start a local host and room
    conform             run the optional conformance suite
    pack                validate, sign, verify, evaluate, accept or run pack connectors
    server              delegate to coalitionkit-server

options:
  -h, --help            show this help message and exit
```

## `coalitionkit up`

```text
usage: coalitionkit up [-h] [--demo | --no-demo] [--members MEMBERS] [--no-web]
                       [--port PORT] [--data-dir DATA_DIR] [--pack PACK] [--reset]
                       [--public-url PUBLIC_URL] [--pace PACE]

options:
  -h, --help            show this help message and exit
  --demo, --no-demo     also create the scripted demo coalition and print its viewer
                        tokens
  --members MEMBERS     members in the --demo coalition
  --no-web
  --port PORT
  --data-dir DATA_DIR
  --pack PACK
  --reset
  --public-url PUBLIC_URL
                        the HTTPS address other devices reach this host at, such as a
                        tunnel's; the host still listens on 127.0.0.1 and links, QR
                        codes and origin checks use this address
  --pace PACE           seconds between demo steps (0 runs at once)
```

## `coalitionkit server`

```text
usage: coalitionkit-server [-h] {serve,init-coalition,invite,status} ...

positional arguments:
  {serve,init-coalition,invite,status}

options:
  -h, --help            show this help message and exit
```

## `coalitionkit server serve`

```text
usage: coalitionkit-server serve [-h]

options:
  -h, --help  show this help message and exit
```

## `coalitionkit pack`

```text
usage: coalitionkit-pack [-h] {connectors,eval,accept,validate,sign,verify} ...

Pack validation, signing, evaluation and isolated connectors. Exit 0 ok, 1 failed, 2 bad
usage.

positional arguments:
  {connectors,eval,accept,validate,sign,verify}
    connectors          print or isolate pack connectors
    eval                run scripted pack scenarios on a host
    accept              run a pack's whole acceptance journey
    validate            check every pack rule (signature not required)
    sign                write pack.sig with an Ed25519 key (PKCS8 PEM)
    verify              verify pack.sig

options:
  -h, --help            show this help message and exit
```

## `coalitionkit conform`

```text
usage: coalitionkit conform [-h] --target TARGET --level {member,vault,host,surface}
                            [--invite INVITE] [--invites-file INVITES_FILE]
                            [--redeem-url REDEEM_URL] [--operator {reference}]
                            [--admin-token-file ADMIN_TOKEN_FILE] [--key KEY]
                            [--timeout TIMEOUT]

Coalition Protocol conformance probes

options:
  -h, --help            show this help message and exit
  --target TARGET       Signed agent card URL
  --level {member,vault,host,surface}
  --invite INVITE       Operator invitation code
  --invites-file INVITES_FILE
                        UTF-8 file, one invitation per line
  --redeem-url REDEEM_URL
                        Operator endpoint accepting invitation and inline card
  --operator {reference}
  --admin-token-file ADMIN_TOKEN_FILE
  --key KEY             Unencrypted Ed25519 PKCS8 PEM report signing key
  --timeout TIMEOUT     HTTP timeout in seconds
```
