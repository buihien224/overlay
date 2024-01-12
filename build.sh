#!/bin/bash
dir=$(pwd)


recp() {
	apkp=$(ls $dir/overlay | grep $1 | head -1)
	apk1=$(echo $apkp | cut -d'-' -f2)
	apk2=hypervs.$apk1

	echo -e "\e[91mBuild $apkp\e[0m"

	java -jar $dir/bin/apktool.jar b -f $dir/overlay/$apkp -o output/$apk2.temp 

	if [[ -f output/$apk2.temp  ]]; then
		./bin/zipalign -p -v 4 output/$apk2.temp output/$apk2.apk
		apksigner sign --ks $dir/bin/miuivs --ks-pass pass:linkcute output/$apk2.apk
		rm -rf output/$apk2.temp output/$apk2.apk.idsig
		echo "Success"

	else
		echo $1 : $apk2 >> $dir/error.log
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
		num=$(echo $path | cut -d'-' -f1)
		recp $num
	done
else
	recp $pick
fi

rm -rf $(find -type d -name build)


#sed -i 's/versionName: [^ ]*/versionName: VS-1.0.ST/g' $(find -type f -name apktool.yml)
#sed -i 's/apkFileName: miuivs\./apkFileName: HyperVS\./g' $(find -type f -name apktool.yml)
#sed -i 's/package="miuivs/package="hypervs/g' $(find -type f -name AndroidManifest.xml)
