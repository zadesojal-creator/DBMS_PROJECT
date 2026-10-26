-- ==============================================================================
-- StockTrade 100 Indian Companies Seed Data (seed_companies.sql)
-- Across 14 Distinct Sectors with Plausible Reference Prices
-- ==============================================================================

-- 1. Insert 100 Companies
INSERT INTO Stocks (symbol, company_name, sector, exchange, status) VALUES
-- Information Technology
('TCS', 'Tata Consultancy Services Ltd', 'Information Technology', 'NSE', 'ACTIVE'),
('INFY', 'Infosys Ltd', 'Information Technology', 'NSE', 'ACTIVE'),
('WIPRO', 'Wipro Ltd', 'Information Technology', 'NSE', 'ACTIVE'),
('HCLTECH', 'HCL Technologies Ltd', 'Information Technology', 'NSE', 'ACTIVE'),
('TECHM', 'Tech Mahindra Ltd', 'Information Technology', 'NSE', 'ACTIVE'),
('LTIM', 'LTIMindtree Ltd', 'Information Technology', 'NSE', 'ACTIVE'),
('PERSISTENT', 'Persistent Systems Ltd', 'Information Technology', 'NSE', 'ACTIVE'),
('COFORGE', 'Coforge Ltd', 'Information Technology', 'NSE', 'ACTIVE'),

-- Banking
('HDFCBANK', 'HDFC Bank Ltd', 'Banking', 'NSE', 'ACTIVE'),
('ICICIBANK', 'ICICI Bank Ltd', 'Banking', 'NSE', 'ACTIVE'),
('SBIN', 'State Bank of India', 'Banking', 'NSE', 'ACTIVE'),
('KOTAKBANK', 'Kotak Mahindra Bank Ltd', 'Banking', 'NSE', 'ACTIVE'),
('AXISBANK', 'Axis Bank Ltd', 'Banking', 'NSE', 'ACTIVE'),
('INDUSINDBK', 'IndusInd Bank Ltd', 'Banking', 'NSE', 'ACTIVE'),
('BANKBARODA', 'Bank of Baroda', 'Banking', 'NSE', 'ACTIVE'),
('PNB', 'Punjab National Bank', 'Banking', 'NSE', 'ACTIVE'),

-- Financial Services & NBFC
('BAJFINANCE', 'Bajaj Finance Ltd', 'Financial Services', 'NSE', 'ACTIVE'),
('BAJAJFINSV', 'Bajaj Finserv Ltd', 'Financial Services', 'NSE', 'ACTIVE'),
('CHOLAFIN', 'Cholamandalam Investment and Finance', 'Financial Services', 'NSE', 'ACTIVE'),
('MUTHOOTFIN', 'Muthoot Finance Ltd', 'Financial Services', 'NSE', 'ACTIVE'),
('SHRIRAMFIN', 'Shriram Finance Ltd', 'Financial Services', 'NSE', 'ACTIVE'),
('HDFCLIFE', 'HDFC Life Insurance Co Ltd', 'Financial Services', 'NSE', 'ACTIVE'),
('SBILIFE', 'SBI Life Insurance Co Ltd', 'Financial Services', 'NSE', 'ACTIVE'),
('ICICIPRULI', 'ICICI Prudential Life Insurance', 'Financial Services', 'NSE', 'ACTIVE'),

-- Energy, Oil & Gas
('RELIANCE', 'Reliance Industries Ltd', 'Energy & Power', 'NSE', 'ACTIVE'),
('ONGC', 'Oil & Natural Gas Corp Ltd', 'Energy & Power', 'NSE', 'ACTIVE'),
('IOC', 'Indian Oil Corporation Ltd', 'Energy & Power', 'NSE', 'ACTIVE'),
('BPCL', 'Bharat Petroleum Corp Ltd', 'Energy & Power', 'NSE', 'ACTIVE'),
('GAIL', 'GAIL (India) Ltd', 'Energy & Power', 'NSE', 'ACTIVE'),
('COALINDIA', 'Coal India Ltd', 'Energy & Power', 'NSE', 'ACTIVE'),
('NTPC', 'NTPC Ltd', 'Energy & Power', 'NSE', 'ACTIVE'),
('POWERGRID', 'Power Grid Corporation of India', 'Energy & Power', 'NSE', 'ACTIVE'),

-- Automotive
('TATAMOTORS', 'Tata Motors Ltd', 'Automotive', 'NSE', 'ACTIVE'),
('MARUTI', 'Maruti Suzuki India Ltd', 'Automotive', 'NSE', 'ACTIVE'),
('M&M', 'Mahindra & Mahindra Ltd', 'Automotive', 'NSE', 'ACTIVE'),
('BAJAJ-AUTO', 'Bajaj Auto Ltd', 'Automotive', 'NSE', 'ACTIVE'),
('HEROMOTOCO', 'Hero MotoCorp Ltd', 'Automotive', 'NSE', 'ACTIVE'),
('EICHERMOT', 'Eicher Motors Ltd', 'Automotive', 'NSE', 'ACTIVE'),
('TVSMOTOR', 'TVS Motor Company Ltd', 'Automotive', 'NSE', 'ACTIVE'),
('ASHOKLEY', 'Ashok Leyland Ltd', 'Automotive', 'NSE', 'ACTIVE'),

-- Pharmaceuticals & Healthcare
('SUNPHARMA', 'Sun Pharmaceutical Industries', 'Healthcare & Pharma', 'NSE', 'ACTIVE'),
('DRREDDY', 'Dr. Reddy Laboratories Ltd', 'Healthcare & Pharma', 'NSE', 'ACTIVE'),
('CIPLA', 'Cipla Ltd', 'Healthcare & Pharma', 'NSE', 'ACTIVE'),
('APOLLOHOSP', 'Apollo Hospitals Enterprise Ltd', 'Healthcare & Pharma', 'NSE', 'ACTIVE'),
('DIVISLAB', 'Divi Laboratories Ltd', 'Healthcare & Pharma', 'NSE', 'ACTIVE'),
('LUPIN', 'Lupin Ltd', 'Healthcare & Pharma', 'NSE', 'ACTIVE'),
('TORNTPHARM', 'Torrent Pharmaceuticals Ltd', 'Healthcare & Pharma', 'NSE', 'ACTIVE'),
('BIOCON', 'Biocon Ltd', 'Healthcare & Pharma', 'NSE', 'ACTIVE'),

-- FMCG & Consumer Goods
('HINDUNILVR', 'Hindustan Unilever Ltd', 'Consumer Goods & FMCG', 'NSE', 'ACTIVE'),
('ITC', 'ITC Ltd', 'Consumer Goods & FMCG', 'NSE', 'ACTIVE'),
('NESTLEIND', 'Nestle India Ltd', 'Consumer Goods & FMCG', 'NSE', 'ACTIVE'),
('BRITANNIA', 'Britannia Industries Ltd', 'Consumer Goods & FMCG', 'NSE', 'ACTIVE'),
('TATACONSUM', 'Tata Consumer Products Ltd', 'Consumer Goods & FMCG', 'NSE', 'ACTIVE'),
('DABUR', 'Dabur India Ltd', 'Consumer Goods & FMCG', 'NSE', 'ACTIVE'),
('MARICO', 'Marico Ltd', 'Consumer Goods & FMCG', 'NSE', 'ACTIVE'),
('GODREJCP', 'Godrej Consumer Products Ltd', 'Consumer Goods & FMCG', 'NSE', 'ACTIVE'),

-- Metals & Mining
('TATASTEEL', 'Tata Steel Ltd', 'Metals & Mining', 'NSE', 'ACTIVE'),
('JSWSTEEL', 'JSW Steel Ltd', 'Metals & Mining', 'NSE', 'ACTIVE'),
('HINDALCO', 'Hindalco Industries Ltd', 'Metals & Mining', 'NSE', 'ACTIVE'),
('VEDL', 'Vedanta Ltd', 'Metals & Mining', 'NSE', 'ACTIVE'),
('JINDALSTEL', 'Jindal Steel & Power Ltd', 'Metals & Mining', 'NSE', 'ACTIVE'),
('NMDC', 'NMDC Ltd', 'Metals & Mining', 'NSE', 'ACTIVE'),
('SAIL', 'Steel Authority of India Ltd', 'Metals & Mining', 'NSE', 'ACTIVE'),
('NATIONALUM', 'National Aluminium Co Ltd', 'Metals & Mining', 'NSE', 'ACTIVE'),

-- Infrastructure, Construction & Real Estate
('LT', 'Larsen & Toubro Ltd', 'Infrastructure & Construction', 'NSE', 'ACTIVE'),
('DLF', 'DLF Ltd', 'Real Estate', 'NSE', 'ACTIVE'),
('GODREJPROP', 'Godrej Properties Ltd', 'Real Estate', 'NSE', 'ACTIVE'),
('OBEROIRLTY', 'Oberoi Realty Ltd', 'Real Estate', 'NSE', 'ACTIVE'),
('ULTRACEMCO', 'UltraTech Cement Ltd', 'Cement & Building Materials', 'NSE', 'ACTIVE'),
('GRASIM', 'Grasim Industries Ltd', 'Cement & Building Materials', 'NSE', 'ACTIVE'),
('AMBUJACEM', 'Ambuja Cements Ltd', 'Cement & Building Materials', 'NSE', 'ACTIVE'),
('ACC', 'ACC Ltd', 'Cement & Building Materials', 'NSE', 'ACTIVE'),

-- Chemicals & Fertilizers
('PIDILITIND', 'Pidilite Industries Ltd', 'Chemicals', 'NSE', 'ACTIVE'),
('SRF', 'SRF Ltd', 'Chemicals', 'NSE', 'ACTIVE'),
('AARTIIND', 'Aarti Industries Ltd', 'Chemicals', 'NSE', 'ACTIVE'),
('DEEPAKNTR', 'Deepak Nitrite Ltd', 'Chemicals', 'NSE', 'ACTIVE'),
('TATACHEM', 'Tata Chemicals Ltd', 'Chemicals', 'NSE', 'ACTIVE'),
('UPL', 'UPL Ltd', 'Chemicals', 'NSE', 'ACTIVE'),
('PIIND', 'PI Industries Ltd', 'Chemicals', 'NSE', 'ACTIVE'),
('COROMANDEL', 'Coromandel International Ltd', 'Chemicals', 'NSE', 'ACTIVE'),

-- Telecommunications & Media
('BHARTIARTL', 'Bharti Airtel Ltd', 'Telecom & Media', 'NSE', 'ACTIVE'),
('IDEA', 'Vodafone Idea Ltd', 'Telecom & Media', 'NSE', 'ACTIVE'),
('TATACOMM', 'Tata Communications Ltd', 'Telecom & Media', 'NSE', 'ACTIVE'),
('SUNTV', 'Sun TV Network Ltd', 'Telecom & Media', 'NSE', 'ACTIVE'),
('ZEEL', 'Zee Entertainment Enterprises', 'Telecom & Media', 'NSE', 'ACTIVE'),
('PVRINOX', 'PVR INOX Ltd', 'Telecom & Media', 'NSE', 'ACTIVE'),

-- Retail, Logistics & Services
('TITAN', 'Titan Company Ltd', 'Retail & Consumer Services', 'NSE', 'ACTIVE'),
('TRENT', 'Trent Ltd', 'Retail & Consumer Services', 'NSE', 'ACTIVE'),
('DMART', 'Avenue Supermarts Ltd', 'Retail & Consumer Services', 'BSE', 'ACTIVE'),
('CONCOR', 'Container Corporation of India', 'Logistics', 'NSE', 'ACTIVE'),
('BLUEDART', 'Blue Dart Express Ltd', 'Logistics', 'NSE', 'ACTIVE'),
('ZOMATO', 'Zomato Ltd', 'Retail & Consumer Services', 'NSE', 'ACTIVE'),
('DELHIVERY', 'Delhivery Ltd', 'Logistics', 'NSE', 'ACTIVE'),
('IRCTC', 'Indian Railway Catering & Tourism', 'Retail & Consumer Services', 'NSE', 'ACTIVE'),

-- Defense & Aerospace
('HAL', 'Hindustan Aeronautics Ltd', 'Defense & Aerospace', 'NSE', 'ACTIVE'),
('BEL', 'Bharat Electronics Ltd', 'Defense & Aerospace', 'NSE', 'ACTIVE'),
('BDL', 'Bharat Dynamics Ltd', 'Defense & Aerospace', 'NSE', 'ACTIVE'),
('MAZDOCK', 'Mazagon Dock Shipbuilders Ltd', 'Defense & Aerospace', 'NSE', 'ACTIVE'),

-- Capital Goods & Electrical
('SIEMENS', 'Siemens Ltd', 'Capital Goods', 'NSE', 'ACTIVE'),
('ABB', 'ABB India Ltd', 'Capital Goods', 'NSE', 'ACTIVE'),
('BHEL', 'Bharat Heavy Electricals Ltd', 'Capital Goods', 'NSE', 'ACTIVE'),
('HAVELLS', 'Havells India Ltd', 'Consumer Electricals', 'NSE', 'ACTIVE'),
('POLYCAB', 'Polycab India Ltd', 'Consumer Electricals', 'NSE', 'ACTIVE'),
('CGPOWER', 'CG Power & Industrial Solutions', 'Capital Goods', 'NSE', 'ACTIVE')
ON DUPLICATE KEY UPDATE company_name=VALUES(company_name);

-- 2. Populate Current_Prices for all seeded stocks
-- Initial reference prices calibrated to approximate real market baselines
-- Each stock receives its genuine stock-specific previous close and daily range (never hardcoded 995.00)
INSERT INTO Current_Prices (stock_id, price, previous_close, day_open, day_high, day_low, volume, updated_at)
SELECT 
    sub.id,
    sub.ref_price AS price,
    -- prev_close is derived directly from each stock's calibrated reference price
    ROUND(sub.ref_price * 0.995, 2) AS previous_close,
    ROUND(sub.ref_price * 0.998, 2) AS day_open,
    ROUND(sub.ref_price * 1.015, 2) AS day_high,
    ROUND(sub.ref_price * 0.985, 2) AS day_low,
    150000 + (sub.id * 1234 % 50000) AS volume,
    CURRENT_TIMESTAMP
FROM (
    SELECT 
        s.id,
        CASE s.symbol
            WHEN 'TCS' THEN 4210.50 WHEN 'INFY' THEN 1890.25 WHEN 'WIPRO' THEN 535.40 WHEN 'HCLTECH' THEN 1780.00
            WHEN 'TECHM' THEN 1620.00 WHEN 'LTIM' THEN 5800.00 WHEN 'PERSISTENT' THEN 5100.00 WHEN 'COFORGE' THEN 6800.00
            WHEN 'HDFCBANK' THEN 1675.50 WHEN 'ICICIBANK' THEN 1240.80 WHEN 'SBIN' THEN 810.20 WHEN 'KOTAKBANK' THEN 1860.00
            WHEN 'AXISBANK' THEN 1170.00 WHEN 'INDUSINDBK' THEN 1350.00 WHEN 'BANKBARODA' THEN 245.50 WHEN 'PNB' THEN 105.20
            WHEN 'BAJFINANCE' THEN 7250.00 WHEN 'BAJAJFINSV' THEN 1840.00 WHEN 'CHOLAFIN' THEN 1480.00 WHEN 'MUTHOOTFIN' THEN 1920.00
            WHEN 'SHRIRAMFIN' THEN 3100.00 WHEN 'HDFCLIFE' THEN 720.00 WHEN 'SBILIFE' THEN 1690.00 WHEN 'ICICIPRULI' THEN 740.00
            WHEN 'RELIANCE' THEN 2980.00 WHEN 'ONGC' THEN 295.40 WHEN 'IOC' THEN 172.50 WHEN 'BPCL' THEN 345.00
            WHEN 'GAIL' THEN 215.00 WHEN 'COALINDIA' THEN 495.00 WHEN 'NTPC' THEN 410.00 WHEN 'POWERGRID' THEN 330.00
            WHEN 'TATAMOTORS' THEN 970.00 WHEN 'MARUTI' THEN 12300.00 WHEN 'M&M' THEN 2850.00 WHEN 'BAJAJ-AUTO' THEN 9950.00
            WHEN 'HEROMOTOCO' THEN 5200.00 WHEN 'EICHERMOT' THEN 4750.00 WHEN 'TVSMOTOR' THEN 2600.00 WHEN 'ASHOKLEY' THEN 220.00
            WHEN 'SUNPHARMA' THEN 1780.00 WHEN 'DRREDDY' THEN 6600.00 WHEN 'CIPLA' THEN 1580.00 WHEN 'APOLLOHOSP' THEN 6900.00
            WHEN 'DIVISLAB' THEN 4950.00 WHEN 'LUPIN' THEN 2100.00 WHEN 'TORNTPHARM' THEN 3250.00 WHEN 'BIOCON' THEN 360.00
            WHEN 'HINDUNILVR' THEN 2720.00 WHEN 'ITC' THEN 495.00 WHEN 'NESTLEIND' THEN 2550.00 WHEN 'BRITANNIA' THEN 5800.00
            WHEN 'TATACONSUM' THEN 1160.00 WHEN 'DABUR' THEN 610.00 WHEN 'MARICO' THEN 640.00 WHEN 'GODREJCP' THEN 1350.00
            WHEN 'TATASTEEL' THEN 155.00 WHEN 'JSWSTEEL' THEN 980.00 WHEN 'HINDALCO' THEN 680.00 WHEN 'VEDL' THEN 460.00
            WHEN 'JINDALSTEL' THEN 990.00 WHEN 'NMDC' THEN 225.00 WHEN 'SAIL' THEN 135.00 WHEN 'NATIONALUM' THEN 195.00
            WHEN 'LT' THEN 3620.00 WHEN 'DLF' THEN 840.00 WHEN 'GODREJPROP' THEN 3100.00 WHEN 'OBEROIRLTY' THEN 1850.00
            WHEN 'ULTRACEMCO' THEN 11200.00 WHEN 'GRASIM' THEN 2650.00 WHEN 'AMBUJACEM' THEN 620.00 WHEN 'ACC' THEN 2500.00
            WHEN 'PIDILITIND' THEN 3150.00 WHEN 'SRF' THEN 2400.00 WHEN 'AARTIIND' THEN 570.00 WHEN 'DEEPAKNTR' THEN 2750.00
            WHEN 'TATACHEM' THEN 1080.00 WHEN 'UPL' THEN 560.00 WHEN 'PIIND' THEN 4200.00 WHEN 'COROMANDEL' THEN 1650.00
            WHEN 'BHARTIARTL' THEN 1580.00 WHEN 'IDEA' THEN 12.50 WHEN 'TATACOMM' THEN 1980.00 WHEN 'SUNTV' THEN 780.00
            WHEN 'ZEEL' THEN 135.00 WHEN 'PVRINOX' THEN 1550.00 WHEN 'TITAN' THEN 3650.00 WHEN 'TRENT' THEN 7100.00
            WHEN 'DMART' THEN 4850.00 WHEN 'CONCOR' THEN 950.00 WHEN 'BLUEDART' THEN 7800.00 WHEN 'ZOMATO' THEN 265.00
            WHEN 'DELHIVERY' THEN 410.00 WHEN 'IRCTC' THEN 920.00 WHEN 'HAL' THEN 4600.00 WHEN 'BEL' THEN 295.00
            WHEN 'BDL' THEN 1350.00 WHEN 'MAZDOCK' THEN 4300.00 WHEN 'SIEMENS' THEN 6900.00 WHEN 'ABB' THEN 8100.00
            WHEN 'BHEL' THEN 280.00 WHEN 'HAVELLS' THEN 1850.00 WHEN 'POLYCAB' THEN 6800.00 WHEN 'CGPOWER' THEN 720.00
            ELSE 1000.00
        END AS ref_price
    FROM Stocks s
) sub
ON DUPLICATE KEY UPDATE 
    price = VALUES(price),
    previous_close = VALUES(previous_close),
    day_open = VALUES(day_open),
    day_high = VALUES(day_high),
    day_low = VALUES(day_low),
    volume = VALUES(volume),
    updated_at = VALUES(updated_at);
