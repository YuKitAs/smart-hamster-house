* Upload `*.ino` to Arduino

* Remove all weights on the scale and run:

```console
$ python3 weight-and-water.py &
```

* Check logs:

```console
$ tail -f logs/weight-and-water.log
$ grep Weight logs/weight-and-water.log
```

* Check database:

```console
$ influx
> USE water
> SELECT * FROM level
> USE weight
> SELECT * FROM weight [WHERE type='hamster']
```
