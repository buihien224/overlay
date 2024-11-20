#!/bin/bash
dir=$(pwd)
diff="python3 $dir/bin/diff.py"

recp() {
	apkp=$(ls $dir/overlay | grep $1 | head -1)
	apk1=$(echo $apkp | cut -d'-' -f2)
	apk2=hypervs.$apk1

	echo -e "\e[91mBuild $apkp\e[0m"

    rm -rf output/$apk2.apk

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

if [[ -n $1 ]]; then
    pick=$1
else
    # List available overlays and prompt for input
    ls "$dir/overlay"
    echo -n "Enter overlay number: "
    read pick 
fi

handle_diff() {
    apkp=$(ls "$dir/overlay" | grep "$2" | head -1)
    sfile="$dir/overlay/$apkp/res/values-vi/$3.xml"

    $diff "$4" "$sfile"
}

case $pick in
    diff)
        handle_diff "$@"
        ;;
    all)
        for overlay in "$dir/overlay"/*; do
            path=$(basename "$overlay")
            num=$(echo "$path" | cut -d'-' -f1)
            recp "$num"
        done
        ;;
    *)
        recp "$pick"
        ;;
esac


rm -rf $(find -type d -name build)


#sed -i 's/versionName: [^ ]*/versionName: VS-42.ST/g' $(find -type f -name apktool.yml)
#sed -i 's/apkFileName: miuivs\./apkFileName: HyperVS\./g' $(find -type f -name apktool.yml)
#sed -i 's/package="tmp /package="hypervs/g' $(find -type f -name AndroidManifest.xml)
