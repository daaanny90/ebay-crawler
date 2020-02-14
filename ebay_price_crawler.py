from bs4 import BeautifulSoup
from time import sleep
from tqdm import tqdm
from statistics import median
import os
import webbrowser
import requests
import numpy as np
import math


# script to check if a ebay kleinanzeigen item has a price that could generete a profit if sold on normal eBay
#
# 1. It looks from the keywords given the average price (calculated with median and filtering the outliner values) on eBay.
# 2. Than it search the same keywords on eBay kleinanzeigen and compares all the prices with the average price on eBay.
# 3. If the price on eBay kleinanzeigen is lower than the average price on eBay, the script calulates the possible profit, included   #    ebay fees, paypal fees and shipping fees (this means that you can sell the item on eBay with free shipping, the profit is
#    already calculated with it. In this way you can have more chances to sell the item)
# 4. The output will be the min and max price to sell the item in order to make a minimum profit and to stay under the average
#    price, and suggest a price to sell it on eBay. specifying the profit

# remove outliner from array
def clean_outliner(arr):
    mean = np.mean(arr, axis=0)
    sd = np.std(arr, axis=0)
    final_list = [x for x in arr if (x > mean - sd)]
    final_list = [x for x in final_list if (x < mean + sd)]
    return final_list

# fees and realistic selling price
def brutto_sell_price(item_cost, middle_price):
    shipping_fee = 7.5
    min_profit = 20.0
    brutto_price = item_cost + shipping_fee + min_profit
    ebay_fee = brutto_price * 0.1
    paypal_fee = (brutto_price * 0.0249) + 0.35
    sell_price = brutto_price + ebay_fee + paypal_fee
    while sell_price >= middle_price:
        sell_price = sell_price - 5
        
    return sell_price

def calc_profit(item_cost, sell_price):
    profit = sell_price - item_cost - (sell_price*0.1) - ((sell_price*0.0249) + 0.35) - 5.6
    return profit

# item to analyze
print('')
print('#### EBAY CRAWLER ###')
print('')
print('Enter the keywords:')
item = input()

######################
#                    #
# eBay Kleinanzeigen #
#                    #
######################
print('')
print('Look for ' + item + ' on eBay Kleinanzeigen...')
ebaykl_url = 'https://www.ebay-kleinanzeigen.de/'
search_item_ebaykl = ('s-dresden/' + item).replace(' ', '-')
URL_ebaykl = ebaykl_url + item + '/k0l3820r20'
page_ebaykl = requests.get(URL_ebaykl)
soupkl = BeautifulSoup(page_ebaykl.content, 'html.parser')
price_box = soupkl('div', class_='aditem-details')
link_box = soupkl('a', class_='ellipsis')
prices_ebaykl = []
links = []
not_found = soupkl('div', class_='outcomemessage-warning')

# look only in dresden
if not not_found:
    index_saved = [] # important to know wich link must be saved
    for index, el in enumerate(price_box):
        price_el = el.contents[1]
        item_km = 0
        try:
            item_km = int((el.contents[8]).replace(' ', '').replace('km','').replace('ca.',''))
        except:
            print('Distance not found, trying anyway..')
        finally:
            price = price_el.contents[0]
            price = price.replace(' ', '').replace('€','').replace('VB','')
            # take from the page only the elements inside the km range (avoid the far away extra item suggested from ebay)
            if item_km <= 20:
                if (price != ''):
                    prices_ebaykl.append(float(price))
                    index_saved.append(index)
    # save links of items
    for index, el in enumerate(link_box):
        if index in index_saved:
            links.append(el['href'].replace('/','', 1))
    print('Found ' + str(len(links)) + ' items.')
else:
    print('Nothing found in Dresden.')


######################
#                    #
#       eBay         #
#                    #
######################
search_item = item.replace(' ','+')
# param of ebay search:
# - show 200 items on page
# - show only sold items
# - show only "buy now" elements
# - show only used items
print('')
print('Looking for ' + item + ' on eBay...')
URL = 'https://www.ebay.de/sch/i.html?_nkw=' + search_item + '&LH_BIN=1&rt=nc&LH_Sold=1&LH_Complete=1&_ipg=200&LH_ItemCondition=300&LH_ItemCondition=3000'
page = requests.get(URL)

soup = BeautifulSoup(page.content, 'html.parser')
# TODO: check if in the title there are forbidden words like 'defekt'
# results = soup('a',class_='vip')
price = soup('span',class_='bidsold')
fees_raw = soup('span', class_='fee')

# collect all item prices in array
print('')
print('Saving prices from eBay and calculating the average price...')
print('')
prices=[]
for tag in price:
    price = (tag.contents[2]).replace(" ","").replace(',', ".").replace("'","").replace('\n', '')
    if (price != ""):
        price = float(price[:-2].replace(".", "").replace(",","."))
        prices.append(price)

# collect all the fees in array
fees = []
for tag in fees_raw:
    fee = tag.contents[0].replace(' ','').replace('+','').replace('EUR','').replace('Versand','').replace(',','.')
    fees.append(float(fee))

# calc the middle price summing the median of prices and of fees without outliner
middle_price = median(clean_outliner(prices)) + median(clean_outliner(fees))
print('##### Average price of ' + item + ' on eBay is ' + str(middle_price) + ' €. #####')
print('')
    
######################
#                    #
#  Check for profit  #
#                    #
######################
print('Checking if some item on eBay Kleinanzeigen is interesting...')
found = []
for index, i in enumerate(tqdm(prices_ebaykl)):
    sleep(0.05)
    # cut off all the items with a price less than 50% of the middle ebay value (to filter accessories, etc.)
    if i > (middle_price*0.5):
        #set a price to sell the item (this is still confusing but it works now)
        selling_price_min = brutto_sell_price(i, middle_price)
        selling_price_max = brutto_sell_price(middle_price - 15, middle_price)
        profit = middle_price - selling_price_min
        if (middle_price > brutto_sell_price(i, middle_price)):
            # set a minimum profit
            if calc_profit(i, selling_price_min) > 15:
                profit_max = selling_price_max - i
                suggested_sell_price = (selling_price_min + selling_price_max)/2
                text = 'Possible profit for a selling price from ' + str("%.2f" % selling_price_min) + ' € to ' + str("%.2f" % selling_price_max) + ' €: from ' + str( "%.2f" % calc_profit(i, selling_price_min)) + ' to ' + str( "%.2f" % calc_profit(i, selling_price_max)) + ' €. Link is: ' + ebaykl_url + links[index] + '\n' + 'Suggested selling price: ' + str("%.2f" % suggested_sell_price) + '€. Profit will be ' + str("%.2f" % calc_profit(i, suggested_sell_price)) + '€.\n'
                found.append(text)

######################
#                    #
#       Output       #
#                    #
######################
if len(found) > 0:
    print('')
    print('##### ' + str(len(found)) + ' ITEMS FOUND! #####')
    print('')
    for item in found:
        print(item)
else:
    print('')
    print('No interesting items found.')

print('')
print('Done.')


# check page in browser
path = os.path.abspath('temp.html')
url_local = 'file://' + path
with open(path, 'w') as f:
    f.write(soup.prettify())
# webbrowser.open(url_local)

#print(results)