#!/bin/bash
dir=$(pwd)


recp() {
	apkp=$(ls $dir/overlay | grep $1)
	apk1=${apkp:3}
	apk2=miuivs.$apk1

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


#sed -i "s/versionName: miuivs-2.0/versionName: miuivs-2.1.0.4/g" $(find -type f -name apktool.yml)
#sed -i "s/versionCode: '28'/versionCode: '33'/g" $(find -type f -name apktool.yml)
#sed -i "s/targetSdkVersion: '28'/targetSdkVersion: '33'/g" $(find -type f -name apktool.yml)
#sed -i "s/minSdkVersion: '28'/minSdkVersion: '31'/g" $(find -type f -name apktool.yml)
#sed -i "s/compileSdkVersionCodename="6.0-2438415"/compileSdkVersionCodename="6.0-2438415"/g" $(find -type f -name apktool.yml)