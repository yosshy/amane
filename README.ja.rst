=============
python-tempml
=============

TempML は「Temporary Mailing List Manager」の意味です。基本的なアイデア
は QuickML (https://github.com/masui/QuickML )を参考にしていますが、全
く同じではありません。QuickML は汎用的な簡易 ML 管理システムですが、
TempML は元々メール問合せ管理システムとして開発されました。ですので、
TempML は Redmine のようなチケット管理システムに近いです。以下はそれぞ
れの違いです。

QuickML と TempML 主な違い
--------------------------

* ML作成時のメール送信先が異なります。

  * QuickML：最初に指定した任意のメールアカウント(@の前)をその後も使い
    ます。
  * TempML：ML作成専用のメールアカウント宛にメールを送ると、新規のIDで
    メールアカウントが作成され、以後そのアドレスでやり取りが行われます。

* TempML はデフォルトでメンバー登録されるスタッフメンバーを定義できます。
  スタッフメンバーはメール操作によるメンバー削除の対象外になります。
* TempML はマルチテナンシをサポートしています。テナント毎に、ML作成用メー
  ルアカウント、サブジェクトのMLプレフィクス（[ml-00001]等）、スタッフ
  メンバー、クローズ予告／クローズ猶予等を定義できます。
* TempML は添付ファイルでシステムメッセージを付与します。システムメッセー
  ジには ML の基本的な使い方と ML 登録メンバー一覧が含まれます。

Redmine と TempML の主な違い
----------------------------

* Redmine は基本的に Web ベースですが、TempML はメールベースです。
* Redmine はチケットの状態をユーザがカスタマイズ出来ますが、TempML では
  出来ません。
* Redmine はチケットの重要度を定義できますが、TempML では出来ません。
* Redmine はチケット状態のワークフローを定義出来ますが、TempML では出来
  ません。

インストール方法
================

以下のコマンドでインストールして下さい。

::

    # yum install mongodb-server
    # pip install tempml

設定方法
========

TempML には２つの設定ファイルが必要です。

TempML 設定ファイル (/etc/tempml/tempml.conf)
---------------------------------------------

同ファイルのサンプルは以下の通りです。YAML 形式で定義します。

::

    db_name: tempml
    db_url: mongodb://localhost/
    relay_host: localhost
    relay_port: 25
    listen_address: 192.168.0.1
    listen_port: 25
    log_file: /var/log/tempml.log
    domain: example.com

* db_url, db_name ... MongoDB の URI と DB 名です。
* relay_host, relay_port ... メール送信に使用する外部 SMTP サーバの IP
  アドレスとポート番号です。
* listen_address, listen_port ... TempML の smtpd がリッスンする IP ア
  ドレスとポート番号です。
* log_file ... TempML の各種プログラムのログファイルへのフルパスです。
* domain ... TempML smtpd が扱うメールアドレスの @ 以降です。上記の例で
  は \*@example.com 宛のメールを扱います。

テナント設定ファイル (tenant.conf)
----------------------------------

同ファイルのサンプルは以下の通りです。YAML 形式で定義します。

::

    admins:
    - staff1@staff.example.com
    - staff2@staff.example.com
    charset: iso-2022-jp
    ml_name_format: ml-%06d
    new_ml_account: ask
    days_to_close: 7
    days_to_orphan: 7
    readme_msg: |
      メールの返信は %(ml_address)s 宛に送信願います。
      新規アドレスの登録方法: 追加したいメールアドレスを Cc: に記載して上記アドレス宛にメール送信して下さい。
      登録アドレスの削除方法: 削除したいメールアドレスを Cc: に記載し、Subject: を空にして上記アドレス宛にメール送信して下さい。
      問合せのクローズ方法: Subject: に CLOSE のみ記載して上記アドレス宛にメール送信して下さい。
      以下は、スタッフ以外で本メールを受信される登録アドレスの一覧です。
    welcome_msg: |
      %(mailfrom)s 様よりメール頂いた問合せを受け付けました。以降のやりとりは %(ml_address)s 宛に送信願います。
      新規アドレスの登録方法: 追加したいメールアドレスを Cc: に記載して上記アドレス宛にメール送信して下さい。
      登録アドレスの削除方法: 削除したいメールアドレスを Cc: に記載し、Subject: を空にして上記アドレス宛にメール送信して下さい。
      問合せのクローズ方法: Subject: に CLOSE のみ記載して上記アドレス宛にメール送信して下さい。
      以下は、スタッフ以外で本メールを受信される登録アドレスの一覧です。
    remove_msg: |
      %(mailfrom)s 様からのメールにより、以下の登録アドレスを削除しました。
      %(cc)s
      再登録は、現在登録されているアドレスの方かスタッフのみ可能です。
      新規アドレスの登録方法: 追加したいメールアドレスを Cc: に記載して上記アドレス宛にメール送信して下さい。
      登録アドレスの削除方法: 削除したいメールアドレスを Cc: に記載し、Subject: を空にして上記アドレス宛にメール送信して下さい。
      問合せのクローズ方法: Subject: に CLOSE のみ記載して上記アドレス宛にメール送信して下さい。
      以下は、スタッフ以外で本メールを受信される登録アドレスの一覧です。
    goodbye_msg: |
      %(mailfrom)s 様からのメールにより、本件 %(ml_name)s の問合せをクローズしました。
      新規問合せは %(new_ml_address)s 宛にお願い致します。
      以下は、スタッフ以外で本メールを受信される登録アドレスの一覧です。
    reopen_msg: |
      %(mailfrom)s 様からのメールにより、本件 %(ml_name)s の問合せを再開しました。
      新規アドレスの登録方法: 追加したいメールアドレスを Cc: に記載して上記アドレス宛にメール送信して下さい。
      登録アドレスの削除方法: 削除したいメールアドレスを Cc: に記載し、Subject: を空にして上記アドレス宛にメール送信して下さい。
      問合せのクローズ方法: Subject: に CLOSE のみ記載して上記アドレス宛にメール送信して下さい。
      以下は、スタッフ以外で本メールを受信される登録アドレスの一覧です。
    report_subject: 問合せ一覧レポート
    report_format: |
      問合せID: %(ml_name)s\t題名: %(subject)s
      作成日時: %(created)s\t最終更新日時: %(updated)s\t最終更新者: %(by)s
    report_msg: |
      本日の問合せ状況
    
      新規チケット
      ============
      %(new)s
    
      ７日間以内にやりとりのあったチケット
      ====================================
      %(open)s
    
      ７日間以上やりとりの無かったチケット
      ====================================
      %(orphaned)s
    
      最近クローズされたチケット
      ========================
      %(closed)s
    orphaned_subject: 本問合せはもうすぐクローズされます
    orphaned_msg: |
      本メールは自動的に送信されています。
      新規投稿が無い場合、問合せ %(ml_name)s は７日後に自動的にクローズされます。
    closed_subject: 本問合せはクローズされました
    closed_msg: |
      本メールは自動的に送信されています。
      ７日間投稿が無かったため、問合せ %(ml_name)s はクローズされました。
      新規の問合せは %(new_ml_address)s 宛にお願い致します。


* admins ... スタッフのメールアドレスのリストです。
* charset ... メール本文のデフォルトの文字コードです。日本語の場合は
  iso-2022-jp になります。
* ml_name_format ... 新しく作成される ML の @ 以前のフォーマットです。
  ml-%06d とすると ml-000001@<ドメイン名> のようなメールアドレスになり
  ます。
* new_ml_account ... ML の新規作成時に使用されるメールアドレスの @ 以前
  の部分（メールアカウント）です。問合せメール先にすると良いでしょう。
* days_to_orphan ... 最後のメールから一定期間やりとりの無い ML を自動的
  に orphaned（放置状態）として扱うまでの日数です。
* days_to_close ... 放置状態になった ML を自動的に closed（クローズ状
  態）として扱うまでの日数です。
* welcome_msg ... 新規 ML 作成時のメールに添付するテキストファイルのテ
  ンプレートです。
* readme_msg ... 通常の ML メールに添付するテキストファイルのテンプレー
  トです。
* remove_msg ... メンバー削除時のメールに添付するテキストファイルのテン
  プレートです。
* reopen_msg ... 再度 open 状態にされた際のメールに添付するテキストファ
  イルのテンプレートです。
* goodbye_msg ... 手動で ML が closed された際のメールに添付するテキス
  トファイルのテンプレートです。
* report_subject, report_msg, report_format ... 各MLのスタッフに送信す
  る日次報告メールのサブジェクト、本文テンプレート、各 ML の状態表示
  フォーマットです。
* orphaned_subject, orphaned_msg ... 自動的に ML が orphaned にされる際
  に送信されるメールのサブジェクトと本文テンプレートです。
* closed_subject, closed_msg ... 自動的に ML が closed にされる際に送信
  されるメールのサブジェクトと本文テンプレートです。

設定ファイルを作成したら、tempmlctl コマンドで DB に登録します。

::

    $ tempmlctl tenant create <テナント名> --yamlfile <テナント設定ファイル>

テナント情報に修正がある場合は以下のいずれかを行います。

(1) テナント設定ファイルを更新して tempmlctl コマンドを実行する場合::

    $ tempmlctl tenant update <テナント名> --yamlfile <テナント設定ファイル>

(2) 修正部分のオプションを指定して tempmlctl コマン>ドを実行する場合::

    $ tempmlctl tenant update <テナント名> <修正オプション> <新しい設定値> [<修正オプション> <新しい設定値> ...]


サービス開始方法
================

以下のコマンドで tempml_smtpd を実行して下さい。

::

    # tempml_smtpd &
