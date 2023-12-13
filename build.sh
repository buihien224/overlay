#!/bin/bash
dir=$(pwd)


recp() {
	apkp=$(ls $dir/overlay | grep $1)
	apk1=${apkp:3}
	apk2=Hypervs.$apk1

	echo $apkp
	echo $apk1
	echo $apk2

	java -jar $dir/bin/apktool.jar b -f $dir/overlay/$apkp -o output/$apk2.temp 

	if [[ -f output/$apk2.temp  ]]; then
		zipalign -p -v 4 output/$apk2.temp output/$apk2.apk
		apksigner sign --ks $dir/bin/miuivs --ks-pass pass:linkcute output/$apk2.apk
		rm -rf output/$apk2.temp output/$apk2.apk.idsig
		echo "Success"

	else
		echo $apk2 >> $dir/error.log
		echo "Fail"
	fi

}

if [[ $1 ]]; then
	pick=$1
else
	ls $dir/overlay
	echo -n "Enter overlay number: "
	read pick 
fi

if [[ $pick == "all" ]]; then
	for i in $(ls $dir/overlay); do
		path=$(basename $i)
		num=${path:0:2}
		recp $num
	done
else
	recp $pick
fi

rm -rf $(find -type d -name build)


#sed -i 's/versionName: [^ ]*/versionName: VS-1.0.ST/g' $(find -type f -name apktool.yml)
#sed -i 's/apkFileName: miuivs\./apkFileName: HyperVS\./g' $(find -type f -name apktool.yml)
#sed -i 's/package="miuivs/package="hypervs/g' $(find -type f -name AndroidManifest.xml)
