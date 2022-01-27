# Rent Scraping in Japan

Scirpts for crawling rent info in Japan from Internet and analyzing them

config file

```
{
  "sleep_sec": 3,
  "crawler_config": [
    {
      "search_url": "YOUR_URL_1",
      "tag": "YOUR_TAG_1",
      "block_list": [
        "APARTMENT_NAME_1",
        "APARTMENT_NAME_2"
      ]
    },
    {
      "search_url": "YOUR_URL_2",
      "tag": "YOUR_TAG_2",
      "block_list": []
    }
  ]

}
```
