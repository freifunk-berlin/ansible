<?php

if (!function_exists('str_starts_with')) {
    function str_starts_with($str, $start) {
      return (@substr_compare($str, $start, 0, strlen($start))==0);
    }
  }

function classify_firmware($firmware) {

    if (str_starts_with($firmware, 'Hedy') || str_starts_with($firmware, 'Freifunk Potsdam hedy')) {
        $name = 'Hedy';
        preg_match('/Hedy ([0-9]\.[0-9]\.[0-9])/', $firmware, $matches);
        $version = (isset($matches[1])) ? $matches[1] : 'Other';
    } 
    elseif (str_starts_with($firmware, 'Kathleen')) {
        $name = 'Kathleen';
        preg_match('/Kathleen ([0-9]\.[0-9]\.[0-9])/', $firmware, $matches);
        $version = (isset($matches[1])) ? $matches[1] : 'Other';
    }
    elseif (str_starts_with($firmware, 'Freifunk Berlin')) {
        $name = 'Freifunk Berlin';
        preg_match('/Freifunk Berlin ([0-9]\.[0-9]\.[0-9])/', $firmware, $matches);
        $version = (isset($matches[1])) ? $matches[1] : 'Other';
    }    
    elseif (str_starts_with($firmware, 'Freifunk Falter') || str_starts_with($firmware, 'Freifunk-Falter')) {
        $name = 'Falter';
        preg_match('/Freifunk[\s-]Falter ([0-9]\.[0-9]\.[0-9])/', $firmware, $matches);
        $version = (isset($matches[1])) ? $matches[1] : 'Other';
    }
    elseif (str_starts_with($firmware, 'OpenWrt')) {
        $name = 'OpenWrt';
        preg_match('/OpenWrt ([0-9]{2}\.[0-9]{2}\.[0-9]+)/', $firmware, $matches);
        $version = (isset($matches[1])) ? $matches[1] : 'Other';        
        // echo $firmware."\n";
    }
    else {
        $name = 'Other';
        $version = 'Other';
        // echo $firmware."\n";
    }
    
    return array('name' => $name, 'version' => $version);
}
