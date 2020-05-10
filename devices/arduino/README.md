* Upload `*.ino` to Arduino and run:

```console
$ python3 weight-and-water.py &
```

* Check logs:

```console
$ tail -f weight-and-water.log
```

* Check database:

```console
$ influx
> USE water
> SELECT * FROM level
> USE weight
> SELECT * FROM weight
```
