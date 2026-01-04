<?php
// selection.php
// Simple UI to run ai/topstock/selection.py and show generated CSVs.

$stock = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $stock = isset($_POST['id']) ? preg_replace('/[^0-9A-Za-z\.]/', '', $_POST['id']) : '';
    if ($stock !== '') {
        $cmd = 'python3 ./selection.py --id ' . escapeshellarg($stock);
        $outputLines = [];
        $returnVar = 0;
        exec($cmd . ' 2>&1', $outputLines, $returnVar);

        $cmdOutput = implode("\n", $outputLines);

        //locations where selection CSVs may be written
        $csvFolder = "./selection";

        $foundFiles = [];
        if (!is_dir($csvFolder)) die('Error: ' . $csvFolder . ' folder not found.');
        $matches = glob($csvFolder . '/' . $stock . '_*.csv');
        if ($matches && count($matches) > 0) {
            foreach ($matches as $m) $foundFiles[] = $m;
        }
    }
}

function read_csv_rows($file) {
    $rows = [];
    if (!file_exists($file)) return $rows;
    if (($h = fopen($file, 'r')) !== false) {
        while (($data = fgetcsv($h)) !== false) {
            $rows[] = $data;
        }
        fclose($h);
    }
    return $rows;
}

?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Selection Runner</title>
    <style>table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px}</style>
</head>
<body>
    <h2>Run Selection</h2>
    <form method="post">
        Stock code: <input name="id" value="<?php echo htmlspecialchars($stock); ?>"> 
        <button type="submit">Run</button>
    </form>

<?php if (!empty($cmdOutput) || isset($returnVar)): ?>
    <h3>Script Output (exit code <?php echo intval($returnVar); ?>)</h3>
    <pre><?php echo htmlspecialchars($cmdOutput); ?></pre>
<?php endif; ?>

<?php if (isset($foundFiles) && count($foundFiles) > 0): ?>
    <h3>Generated CSVs</h3>
    <?php foreach ($foundFiles as $file): ?>
        <?php $rows = read_csv_rows($file); ?>
        <h4><?php echo htmlspecialchars(basename($file)); ?></h4>
        <?php if (count($rows) > 0): ?>
            <table>
                <thead>
                    <tr>
                    <?php foreach ($rows[0] as $h): ?>
                        <th><?php echo htmlspecialchars($h); ?></th>
                    <?php endforeach; ?>
                    </tr>
                </thead>
                <tbody>
                <?php for ($i = 1; $i < count($rows); $i++): ?>
                    <tr>
                    <?php foreach ($rows[$i] as $c): ?>
                        <td><?php echo htmlspecialchars($c); ?></td>
                    <?php endforeach; ?>
                    </tr>
                <?php endfor; ?>
                </tbody>
            </table>
        <?php else: ?>
            <p>No rows in file.</p>
        <?php endif; ?>
    <?php endforeach; ?>
<?php elseif ($_SERVER['REQUEST_METHOD'] === 'POST'): ?>
    <p>No CSVs found for <?php echo htmlspecialchars($stock); ?>. Check script output above.</p>
<?php endif; ?>

</body>
</html>
