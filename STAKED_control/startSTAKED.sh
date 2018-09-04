#!/bin/bash
source ac
source params
komodod -ac_name=$ac $params -pubkey=038d9f9235eb108acd398e91d5726ea5bccbc510e397be3722375232b37a5e1f76 "${@}"
