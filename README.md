## memo
起動に10分かかる

## command

```
az upgrade
az bicep install

az login --use-device-code

 az account list \
   --refresh \
   --query "[].id" \
   --output table

az account set --subscription <your subscription id>

group_name=20211027HappyHackLineBot

az group create --name ${group_name} --location japaneast

az configure --defaults group=${group_name}

## https://1password.com/jp/password-generator/
az deployment group create --name deployPrj01 --template-file main.bicep \
  --parameters ramdom=<ramdom> \
  --parameters secret=<secret> \
  --parameters access=<access>
  
az deployment group show \
  -g ${group_name} \
  -n deployPrj01 \
  --query properties.outputs.functionAppName.value

cd deployPrj01
npm i
func azure functionapp publish <functionAppName> --build remote

#az group delete --name ${group_name}
```

##

https://azure.github.io/AppService/2021/07/23/Quickstart-Intro-to-Bicep-with-Web-App-plus-DB.html
