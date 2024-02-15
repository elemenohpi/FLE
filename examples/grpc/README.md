# Other Languages: gRPC

**TODO: We have no example in here yet**

With that said, the [gRPC](https://grpc.io/) interface is fully functional if you want to try it.

It currently powers the cli example, which uses a python gRPC client to talk to the `fle` server.

The protobuf files you'll need are in [`../../proto`](../../proto).

The command you would run is something like:
```
protoc --proto_path=proto proto/fle/*.proto --<MY_LANG>_out=<MY_PATH>/fle
```
