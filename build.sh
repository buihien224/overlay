#!/bin/bash
dir=$(cd "$(dirname "$0")" && pwd)
cd "$dir"
diff="python3 $dir/bin/diff.py"
# Số overlay build cùng lúc: JOBS=4 ./build.sh all
JOBS=${JOBS:-$(nproc)}

# aapt2 đi kèm apktool.jar, bung lại mỗi khi đổi jar
if [[ ! -x bin/aapt2 || bin/apktool.jar -nt bin/aapt2 ]]; then
	unzip -p bin/apktool.jar prebuilt/linux/aapt2 > bin/aapt2 && chmod +x bin/aapt2
fi

find_overlay() {
	# Số thứ tự phải khớp chính xác (10 không lấy nhầm 101), còn lại tìm theo tên
	apkp=$(ls "$dir/overlay" | grep -m1 "^$1-")
	[[ -n $apkp ]] || apkp=$(ls "$dir/overlay" | grep -m1 "$1")
	echo "$apkp"
}

recp() {
	apkp=$(find_overlay "$1")
	if [[ -z $apkp ]]; then
		echo -e "\e[91mKhông tìm thấy overlay $1\e[0m"
		return 1
	fi
	apk1=$(echo $apkp | cut -d'-' -f2)
	apk2=vsteam.$apk1
	log=output/$apk2.log

	mkdir -p output
	rm -rf output/$apk2.apk

	{
		java -jar "$dir/bin/apktool.jar" b -f "$dir/overlay/$apkp" --aapt "$dir/bin/aapt2-overlay" -o output/$apk2.temp &&
		./bin/zipalign -p 4 output/$apk2.temp output/$apk2.apk &&
		apksigner sign --ks "$dir/bin/miuivs" --ks-pass pass:linkcute output/$apk2.apk
	} > $log 2>&1
	rm -rf output/$apk2.temp output/$apk2.apk.idsig

	if [[ -f output/$apk2.apk ]]; then
		rm -f $log
		echo -e "\e[92mSuccess\e[0m $apkp"
	else
		echo $1 : $apk2 >> "$dir/error.log"
		echo -e "\e[91mFail\e[0m $apkp"
		grep -i 'error' $log | head -5
		return 1
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
        export dir
        export -f recp find_overlay
        ls "$dir/overlay" | cut -d'-' -f1 | xargs -P "$JOBS" -I{} bash -c 'recp {}'
        echo "Built $(ls output/*.apk 2>/dev/null | wc -l)/$(ls "$dir/overlay" | wc -l) -> output/"
        ;;
    *)
        recp "$pick"
        ;;
esac


rm -rf $(find overlay -type d -name build)


#sed -i 's/versionName: [^ ]*/versionName: VS-42.ST/g' $(find -type f -name apktool.yml)
#sed -i 's/apkFileName: miuivs\./apkFileName: HyperVS\./g' $(find -type f -name apktool.yml)
#sed -i 's/package="tmp /package="hypervs/g' $(find -type f -name AndroidManifest.xml)
