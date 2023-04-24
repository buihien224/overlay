#!/bin/bash
dir=$(pwd)


recp() {
	apk=$(basename $1)
	java -jar $dir/bin/apktool.jar b $1 -o output/$apk.temp 

	if [[ -f output/$apk.temp  ]]; then
		zipalign -p -v 4 output/$apk.temp output/$apk.apk
		apksigner sign --ks $dir/bin/miuivs --ks-pass pass:linkcute output/$apk.apk
		rm -rf output/$apk.temp output/$apk.apk.idsig
		echo "Success"

	else
		echo "Fail"
	fi

}

if [[ $1 == "all" ]]; then
	for i in $(ls overlay); do
		recp overlay/$i
	done
else
	recp $1
fi