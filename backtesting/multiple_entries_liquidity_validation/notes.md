# Notes

Okay so, those notes are gonna be huge ranting file.. I mean it's time for me to put thoughts on paper.. anyway.. here I am facing a little problem.. the problem started when I noticed, that results after year 2022, are going steep down.. with chat bot we manage to crack it, but still, it has many issues.. 

The solution is simple.. create code that measure price action after zone entry, and compare those results with before 2022 and after 2022.. Sounds simple.. but.. now I need to come up with some measurements, that would capture it.. I am gonna measure three things.. chopiness, sharp wick testing the zone with profit of single entry, and occasinal retest of entire zone through stop loss.. So I have three things I wanna measure, the question is HOW!

Choppiness: something like storing bullish candles, and bearish candles.. and count how many times market changed direction.. and therefore divide that number by the overall range the price went in certain time.. and compare it against base range

Sharp wick: ask if first entry was taken by candle with long wick.. I guess it does not matter if the candle is bullish or bearish, and if the wick is upper or lower.. well that's a question.. I guess we need to figure out.. so.. candle body and candle range against zone range

Full zone retest: how many zones were traded by single candle with stop loss.. or max two candles.. sometimes can take it longer.. but the idea stays the same.. and with this behavior, how many times, price continued with correct or opposite direction

Some changes in a plan.. I wanted to make it easy.. and chatbot is right.. as always.. I need to measure real things.. not shits.. 

Choppiness: forget about bullish and bearish candles.. I need to measure swing highs and swing lows.. so how many times price has made new higher high, or higher low, or how many times price has made lower low or lower high, and most importantly, how many times there is change of character.. this should be turbo solid.. for each measured instance.. 

Instances: Sharp wick entered, Full zone retest

Sharp wick: I guess the truth lies not in the bullishness or bearishness of the wick, but in where does the body lies within the candle.. for demand zone.. if the body lies on the bottom, that is whole another story then, when the body lies at the top of the candle, and also measure like percentage of the body against the whole candle.. I think, the very next candle will be more usefull for our measurements.. then measure where the price moves, within 5 or 10 candles.. if it goes back to zone, or continue in correct direction.. sharp wick is gonna be measured like max 20 or 10% body of candle

Full zone retest: Well, here it is pretty simple.. the identification of this instance is one or two big candles ripping through the zone, then I need to find out, if the price consolidate within the zone, or where it goes.. 

So in total: wanna measure two instances, and each instance will have a bit different measurements, but they both will be measured with choppiness.. and choppiness will be also a single instance.. cause sometimes, the price just chop into the zone and chop out of it..

So I made _sharp_wick inner method in Measurements and it kinda sucks.. it is just so one way behave.. I made condition if the body is placed above 60% of the candle.. and if the body is max 20%, which is good.. but it tells me nothing.. I guess, I need to modify this for more usage.. cause current version takes like what, 10% of all wicked zones.. so what, 5 zones a year? yeah right, this tells me a lot of things.. so this is not good.. this sucks hard..

New approach.. calculate where the body stands, and note it.. then let's see the winrate of each placements.. 

if demand:
    upper range = 10
    body range = 20
    lower range = 70
    upper boundary = 100 - upper range = 90
    lower boundary = lower range = 70
    middle pct = (90 + 70) / 2 = 80

is supply:
    upper range = 70
    body range = 20
    lower range = 10
    upper boundary = 100 - upper range = 30
    lower boundary = lower range = 10
    middle pct = 100 - ((30 + 10) / 2) = 80

Great.. this approach was good.. I figure out win/rate of each placement, and found out that this does not matter.. this measurement just sucks.. well not sucks like it's not working.. but sucks like it just doesn't say much.. no value is changing during years.. I mean the pnl is not chaning based on wick.. 

This approach took me like 3 hours of work.. with this I created solid measurement infrastructure, where later new approches can be easily placed..

So let's talk about new approach.. so far I have measured the first candle wick, that does proved nothing.. new approach is a little more complicated.. I need to ask if the first candle ripped through the zone.. we will try if first and if second as well.. cause sometimes the movement takes a little longer.. or the movement crossed two hours.. anyway.. then I need to capture the price action after the enter of the zone.. with enter that basically means after executing.. or selling.. I mean if the first candle rip through the zone.. single candle is entire trade execution..

So let's start with the ripping candle.. then I will figure out the price behavior after it..

Okay so the ripping candle was pretty easy to code.. now, with price behavior.. let's start with something easy.. for example.. where the price end up after 5 or 10 candles.. let's say.. if the price is not in the zone, how far is, and which direction.. how many bases is away ?

After some time.. this tells me nothing.. I mean.. I will see just some number like two zones.. or half zone.. and this shit tells me nothing.. so I need to come up with something better.. something that would capture the movement after ripping through the zone.. 

Okay this is interesting.. I think those data might be actually usefull, I calculated the highest high and lowest low away from the zone, in zones range.. and some of them move, and some of them not.. I guess, later I wanna upgrade it, let's say how the price moves, last 5 candles.. away from the zone.. let's say.. after 10 candles, how did price moved in last 5 candles.. and after 20 candles, how did price moved in last 5 candles.. still the highest high and lowest low.. this way we could capture how much the price is choppy after ripping through the zone.. for example.. if the highest and lows are gonna be similar.. that means price is going sideways... but if the price is like going somewhere.. the numbers are gonna move

3.4.2026 9:11

I stopped after successfull display of last 5 and last 10 candles after 1, 5, 10, 20, 50 candles.. I guess I finally understood, why the values might be in minus.. Cuase if one direction is like 7 zones, the other direction cannot be that big.. so it have to be negative value, in order to make a sense.. So negative values are figured.. now.. why the values after 50, are messy, and are like in hundreds away ?? oh yeah.. and I figured this as well.. cause our array of candles is only 50 candles long.. that's why.. 

Anyway.. I am starting to think that this:
----- Demand ------------------------------------------------------------------------------
+---------+-----------+---------+--------------+------------+---------------+-------------+
| Candles | Downwards | Upwards | Downwards -5 | Upwards -5 | Downwards -10 | Upwards -10 |
+---------+-----------+---------+--------------+------------+---------------+-------------+
|    1    |    3.56   |   2.54  |     0.0      |    0.0     |      0.0      |     0.0     |
|    5    |    3.91   |   2.54  |     3.91     |    2.54    |      0.0      |     0.0     |
|    10   |    3.91   |   2.54  |     2.76     |   -1.02    |      3.91     |     2.54    |
|    20   |    5.84   |   7.82  |     4.82     |    7.82    |      5.84     |     7.82    |
|    30   |    5.84   |   8.08  |    -4.59     |    5.92    |     -3.82     |     8.08    |
|    50   |    5.84   |  14.14  |    -11.11    |   14.14    |     -8.71     |    14.14    |
+---------+-----------+---------+--------------+------------+---------------+-------------+

is gonna tell us really nothing.. well not nothing like nothing at all.. but actually what I can read from this.. let's break it down.. let's just say out loud what does it says, and what not.. first column is number of candles we are looking at once.. second column is the lowest low, from the zone.. which means.. how low the price went after entering zone.. value of 3.56 means, price went 3.56 * zone range away from the zone downwards.. same with upwards.. then I measured how the price high and low looks like at certain indexes (rows), and -5 means, at ceratin index how far the price went in last 5 candles.. same with -10.. how far does the price went, in last 10 candles from certain index (rows).. 

now.. I have pretty good picture about what price does.. it rips through, and then sometimes is consolidating, sometimes is going up and sometimes is going down.. 

I've got a new idea.. maybe I could calculate MA (moving average) and, check where the MA stands at certain indexes.. just like I was doing with highs and lows.. but this way, I could gather real info.. like how the price moves.. and measure more MAs.. 5 or 10 or even 20.. and I could measure how many times, the MA change the direction.. 

One step at the time.. let's start with calculating SMA at certain indexes.. 

Okay this is done.. anyway.. 

4.4.2026 8:53

So.. From what I can tell so far, I am calculating some of the SMAs 5 and 10, at each index.. which is really doing great work.. I think this might be the way of successfull price behavior.. 

Okay so far so good.. 

I have come to conclusion that the upwards and downwards pretty sucks.. but hey.. I have made nice progress with SMAs..

----- Supply ----- P&L: -11.48 ------ | ----- Supply ----- P&L: -12.75 ------
+---------+-------+--------+--------+ | +---------+-------+--------+--------+
| Candles | SMA 5 | SMA 10 | SMA 20 | | | Candles | SMA 5 | SMA 10 | SMA 20 |
+---------+-------+--------+--------+ | +---------+-------+--------+--------+
|    1    |  0.0  |  0.0   |  0.0   | | |    1    |  0.0  |  0.0   |  0.0   |
|    5    | -1.55 |  0.0   |  0.0   | | |    5    |  0.0  |  0.0   |  0.0   |
|    10   |  -1.5 | -1.52  |  0.0   | | |    10   | -1.14 | -0.34  |  0.0   |
|    20   |  -1.0 | -1.05  | -1.29  | | |    20   | -0.47 | -1.43  | -0.89  |
|    30   |  0.0  |  0.0   | -0.33  | | |    30   |  3.69 |  2.37  |  0.0   |
|    40   | -0.54 | -0.16  |  0.0   | | |    40   |  3.04 |  3.45  |  2.91  |
|    50   | -1.82 | -1.65  |  -0.9  | | |    50   |  3.48 |  3.09  |  3.27  |
+---------+-------+--------+--------+ | +---------+-------+--------+--------+
SMA 5 changes: 10                     | SMA 5 changes: 4
SMA 10 changes: 3                     | SMA 10 changes: 3
SMA 20 changes: 1                     | SMA 20 changes: 4

okay.. so we have two trades.. let's compare the values.. and why this might be very good so far

Description for chatbot:
SMA 5 up to 20, at indexes, those are just values how far the SMA is away from the zone in zone lengths, if the value is negative, it means, the SMA is going in opposite direction that we would wan't in order to have successful profitable trade
then there are SMA changes.. that means, how many times, the SMA change direction.. for further
conclusion.. we can clearly see that the first trade has only one change of SMA 20, but 10 changes of SMA 5, which means, that there is strong trend, with swings, but little choppiness on smaller timeframe.. what i mean is, the trend direction is obvious, but there might be some disturbances.. 
on the other hand, the second trade is obviously very choppy.. SMA 5 and SMA 20 has same number of changes.. which means, in last 50 hours, during this trade, there were no clear market indications, where the trend is going..

5.4.2026 8:49

so I am gonna need to sum up those numbers and make an average from it.. so I could compare winners and losers from 2018-2023 against 2024-2025.. The question is how am I gonna do it.. let's take it from the end.. I need winners and losers.. okay.. so I can sort the data based on pnl, and use only data with winners.. what am I measuring? for sure SMA changes, so number of SMA changes on average, 5 and 20, so then I'll know how choppy the market is.. now which direction.. oh yeah.. this one.. I need to come up with something that would summarize the values throughout indexes from 10 to 50.. if value is positive, the SMA is going in our benefit, if value is negative, SMA is going in opposite direction.. okay.. I was thinking a bit.. and I guess I wanna measure, the SMA values.. the highest and the lowest.. that would give me clear picture how flat the market is.. and I don't wanna throw away the downwards and upwards.. with this I can measure how far the price went..

So what do we have so far..

- How idencisive the market is
SMA 5 - changes average
SMA 20 - changes average

- How flat the market is 
SMA 5 - highest SMA throughout indexes
SMA 20 - highest SMA throughout indexes

SMA 5 - lowest SMA throughout indexes
SMA 20 - lowest SMA throughout indexes

- How aggressive the market is
First half - Highest downward value
First half - Highest upward value

Second half - Highest downward value
Second half - Highest upward value
