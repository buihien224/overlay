#!/bin/bash
dir=$(pwd)


recp() {
	apk=$(basename $1)
	java -jar $dir/bin/apktool.jar b -f $1 -o output/$apk.temp 

	if [[ -f output/$apk.temp  ]]; then
		zipalign -p -v 4 output/$apk.temp output/$apk.apk
		apksigner sign --ks $dir/bin/miuivs --ks-pass pass:linkcute output/$apk.apk
		rm -rf output/$apk.temp output/$apk.apk.idsig
		echo "Success"

	else
		echo $apk >> $dir/error.log
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

rm -rf $(find -type d -name build)


#sed -i "s/versionName: miuivs-2.0/versionName: miuivs-2.1.0.4/g" $(find -type f -name apktool.yml)
#sed -i "s/versionCode: '28'/versionCode: '33'/g" $(find -type f -name apktool.yml)
#sed -i "s/targetSdkVersion: '28'/targetSdkVersion: '33'/g" $(find -type f -name apktool.yml)
#sed -i "s/minSdkVersion: '28'/minSdkVersion: '31'/g" $(find -type f -name apktool.yml)
#sed -i "s/compileSdkVersionCodename="6.0-2438415"/compileSdkVersionCodename="6.0-2438415"/g" $(find -type f -name apktool.yml)