<?php
$update=$_REQUEST["update"];
if ($update=="yes"){
    $cmd = 'python3 ./topgun.py';
    try {
        $ret = shell_exec($cmd);
    } catch (Exception $e) {
        die('error=' . $e->getMessage());
    }
}

// Define H1 titles
$H1Array = [
    1 => 'Data 1 - 只保留涨幅在 3% 到 5% 之间的股票',
    2 => 'Data 2 - 剔除量比少于 1 的股票',
    3 => 'Data 3 - 剔除换手率低于 5% 或者高于 10% 的股票',
    4 => 'Data 4 - 剔除流通市值小于 50 亿或者高于 200 亿的股票',
    5 => 'Data 5 - 股价必须在全天的均价上方运行'
];

// Read CSV files into arrays
$dataFiles = [
    1 => "./results/data1.csv",
    2 => "./results/data2.csv",
    3 => "./results/data3.csv",
    4 => "./results/data4.csv",
    5 => "./results/data5.csv"
];

// Load each CSV file into corresponding arrays
$headers = [];
$updateTimes = [];
$dataArrays = [];
for ($i = 1; $i <= count($dataFiles); $i++) {
    // check if file exists
    $csvFile = $dataFiles[$i];
    if (!file_exists($csvFile)) {
        echo "<p>Error: " . $csvFile . " file not found.</p>";
        exit;
    }
    
    // check the update time of the file
    $updateTimes[$i] = date("Y-m-d H:i:s", filemtime($csvFile));

    // Read CSV data
    $dataArrays[$i] = [];
    if (($handle = fopen($csvFile, "r")) !== false) {
        $headers[$i] = fgetcsv($handle);
        while (($row = fgetcsv($handle)) !== false) {
            // Add link to stock code
            $row[1] = createStockLink(htmlspecialchars($row[1]));
            $dataArrays[$i][] = $row;
        }
        fclose($handle);
    } else {
        echo "<p>Error: Unable to open the " . $csvFile . " file.</p>";
    }
}

// function to create link for stock code
function createStockLink($code) {
    $prefix = "sz";
    switch (substr($code, 0, 2)) {
        case "60":
            $prefix = "sh";
            break;
        case "90":
            $prefix = "sh";
            break;
        case "68":
            $prefix = "kcb/";
            break;
        case "00":
            $prefix = "sz";
            break;
        case "20":
            $prefix = "sz";
            break;
        case "30":
            $prefix = "sz";
            break;
        case "92":
            $prefix = "bj/";
            break;
        default:
            $prefix = "sz";
    }

    return "<a href='https://quote.eastmoney.com/" . $prefix . $code . "' target='_blank'>" . $code . "</a>";
}

// Display the data in an HTML table
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Potential Stocks</title>
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        /* Collapse/expand controls */
        h1.toggle {
            cursor: pointer;
            user-select: none;
        }
        h1.toggle .indicator {
            display: inline-block;
            width: 1.2em;
            text-align: center;
            margin-right: 0.5em;
            font-weight: bold;
        }
        table.collapsible {
            transition: all 0.15s ease;
        }
        table.collapsible.hidden {
            display: none;
        }
    </style>
</head>
<body>
    <?php
    for ($i = 1; $i <= count($headers); $i++) {
        echo "<h1>" . htmlspecialchars($H1Array[$i]) . " (" . $updateTimes[$i] . ")</h1>";
        echo "<table>";
        echo "<thead><tr>";
        foreach ($headers[$i] as $column) {
            echo "<th>" . htmlspecialchars($column) . "</th>";
        }
        echo "</tr></thead><tbody>";
        foreach ($dataArrays[$i] as $row) {
            echo "<tr>";
            foreach ($row as $cell) {
                echo "<td>" . htmlspecialchars($cell) . "</td>";
            }
            echo "</tr>";
        }
        echo "</tbody></table>";
    }
    ?>
    
    <script>
        document.addEventListener('DOMContentLoaded', function () {
            document.querySelectorAll('h1').forEach(function (h) {
                var tbl = h.nextElementSibling;
                if (!tbl || tbl.tagName.toLowerCase() !== 'table') return;
                h.classList.add('toggle');
                var ind = document.createElement('span');
                ind.className = 'indicator';
                ind.textContent = '[+]';
                h.insertBefore(ind, h.firstChild);
                tbl.classList.add('collapsible', 'hidden');
                h.setAttribute('aria-expanded', 'false');
                h.addEventListener('click', function () {
                    var isHidden = tbl.classList.toggle('hidden');
                    h.setAttribute('aria-expanded', String(!isHidden));
                    ind.textContent = isHidden ? '[+]' : '[-]';
                });
            });
        });
    </script>
</body>
</html>