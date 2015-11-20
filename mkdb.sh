#!/bin/sh

FILE_ROOT=hashroot
FN=hashfs.sqlite3

if [ -f $FN ]
then
	echo Database $FN already exists.  Will not overwrite
	exit 1
fi
if [ -d $FILE_ROOT ]
then
	echo File root $FILE_ROOT already exists.  Will not overwrite
	exit 1
fi

mkdir -p $FILE_ROOT

sqlite3 $FN < hashfs.schema

