#!/bin/sh

FN=hashfs.sqlite3

rm -f $FN
sqlite3 $FN < hashfs.schema

