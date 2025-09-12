<?php
// ini_set('display_errors', 1);
// ini_set('display_startup_errors', 1);
// error_reporting(E_ALL ^ E_NOTICE);

require_once('classify-firmware.php');
header("Content-Type: text/plain");

$url="https://hopglass.berlin.freifunk.net/meshviewer.json";
//  Initiate curl
$ch = curl_init();
// Will return the response, if false it print the response
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
// Set the url
curl_setopt($ch, CURLOPT_URL,$url);
// Execute
$result=curl_exec($ch);
// Closing
curl_close($ch);

// JSON as an object
$json = json_decode($result);

// firmwares
$firmwares = array ('Other' => array(), 'OpenWrt' => array(), 'Freifunk Berlin' => array(), 'Kathleen' => array(),'Hedy' => array(), 'Falter' => array());

foreach($json->nodes as $node) {
    // Only use online nodes
    if($node->is_online === true) {
        $firmware = classify_firmware($node->firmware->release);
        $firmwares[$firmware['name']][$firmware['version']]++;
    }
    // echo $node->nodeinfo->software->firmware->release.': '.$firmware['name']." - " .$firmware['version']."\n";
}

// Output Exporter
echo '# HELP freifunk_firmware_version_counter nodes with specific version'."\n";
echo '# TYPE freifunk_firmware_version_counter gauge'."\n";
foreach ($firmwares as $key => $val) {
    ksort($firmwares[$key]);
    foreach ($firmwares[$key] as $version => $count) {
        echo 'freifunk_firmware_version_counter{name="'.$key.'",version="'.$version.'"} '.$count."\n";
    }
}

// var_dump ($firmwares);
