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

$csvFile = "./results/data1.csv";
if (!file_exists($csvFile)) {
    echo "<p>Error: "+ $csvFile +" file not found.</p>";
    exit;
}
$data1 = [];
if (($handle = fopen($csvFile, "r")) !== false) {
    $header1 = fgetcsv($handle);
    while (($row = fgetcsv($handle)) !== false) {
        $data1[] = $row;
    }
    fclose($handle);
} else {
    echo "<p>Error: Unable to open the "+ $csvFile +" file.</p>";
}

$csvFile = "./results/data2.csv";
if (!file_exists($csvFile)) {
    echo "<p>Error: "+ $csvFile +" file not found.</p>";
    exit;
}
$data2 = [];
if (($handle = fopen($csvFile, "r")) !== false) {
    $header2 = fgetcsv($handle);
    while (($row = fgetcsv($handle)) !== false) {
        $data2[] = $row;
    }
    fclose($handle);
} else {
    echo "<p>Error: Unable to open the "+ $csvFile +" file.</p>";
}

$csvFile = "./results/data3.csv";
if (!file_exists($csvFile)) {
    echo "<p>Error: "+ $csvFile +" file not found.</p>";
    exit;
}
$data3 = [];
if (($handle = fopen($csvFile, "r")) !== false) {
    $header3 = fgetcsv($handle);
    while (($row = fgetcsv($handle)) !== false) {
        $data3[] = $row;
    }
    fclose($handle);
} else {
    echo "<p>Error: Unable to open the "+ $csvFile +" file.</p>";
}

$csvFile = "./results/data4.csv";
if (!file_exists($csvFile)) {
    echo "<p>Error: "+ $csvFile +" file not found.</p>";
    exit;
}
$data4 = [];
if (($handle = fopen($csvFile, "r")) !== false) {
    $header4 = fgetcsv($handle);
    while (($row = fgetcsv($handle)) !== false) {
        $data4[] = $row;
    }
    fclose($handle);
} else {
    echo "<p>Error: Unable to open the "+ $csvFile +" file.</p>";
}

$csvFile = "./results/data5.csv";
if (!file_exists($csvFile)) {
    echo "<p>Error: "+ $csvFile +" file not found.</p>";
}
$data5 = [];
if (($handle = fopen($csvFile, "r")) !== false) {
    $header5 = fgetcsv($handle);
    while (($row = fgetcsv($handle)) !== false) {
        $data5[] = $row;
    }
    fclose($handle);
} else {
    echo "<p>Error: Unable to open the "+ $csvFile +" file.</p>";
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
    <h1>Data 1 - 只保留涨幅在 3% 到 5% 之间的股票</h1>
    <table>
        <thead>
            <tr>
                <?php foreach ($header1 as $column): ?>
                    <th><?php echo htmlspecialchars($column); ?></th>
                <?php endforeach; ?>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($data1 as $row): ?>
                <tr>
                    <?php foreach ($row as $cell): ?>
                        <td><?php echo htmlspecialchars($cell); ?></td>
                    <?php endforeach; ?>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <h1>Data 2 - 剔除量比少于 1 的股票</h1>
    <table>
        <thead>
            <tr>
                <?php foreach ($header2 as $column): ?>
                    <th><?php echo htmlspecialchars($column); ?></th>
                <?php endforeach; ?>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($data2 as $row): ?>
                <tr>
                    <?php foreach ($row as $cell): ?>
                        <td><?php echo htmlspecialchars($cell); ?></td>
                    <?php endforeach; ?>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <h1>Data 3 - 剔除换手率低于 5% 或者高于 10% 的股票</h1>
    <table>
        <thead>
            <tr>
                <?php foreach ($header3 as $column): ?>
                    <th><?php echo htmlspecialchars($column); ?></th>
                <?php endforeach; ?>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($data3 as $row): ?>
                <tr>
                    <?php foreach ($row as $cell): ?>
                        <td><?php echo htmlspecialchars($cell); ?></td>
                    <?php endforeach; ?>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <h1>Data 4 - 剔除流通市值小于 50 亿或者高于 200 亿的股票</h1>
    <table>
        <thead>
            <tr>
                <?php foreach ($header4 as $column): ?>
                    <th><?php echo htmlspecialchars($column); ?></th>
                <?php endforeach; ?>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($data4 as $row): ?>
                <tr>
                    <?php foreach ($row as $cell): ?>
                        <td><?php echo htmlspecialchars($cell); ?></td>
                    <?php endforeach; ?>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <h1>Data 5 - 股价必须在全天的均价上方运行</h1>
    <table>
        <thead>
            <tr>
                <?php foreach ($header5 as $column): ?>
                    <th><?php echo htmlspecialchars($column); ?></th>
                <?php endforeach; ?>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($data5 as $row): ?>
                <tr>
                    <?php foreach ($row as $cell): ?>
                        <td><?php echo htmlspecialchars($cell); ?></td>
                    <?php endforeach; ?>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
    
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