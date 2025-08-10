import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gpt_summarizer import generate_structured_summary
from dotenv import load_dotenv

ARTICLE_TEXT = """
일 평균 30억 건을 처리하는 결제 시스템의 DB를 Vitess로 교체하기 - 2. 개발 및 운영기
Share on Facebook
Share on X
Share on Line
Copy Link
Share on はてなブックマーク
들어가며
안녕하세요. LINE Billing Platform 개발 팀의 김영재, 이정재입니다. LINE Billing Platform 개발 팀에서는 LINE 앱 내 여러 서비스에서 사용하는 결제, 포인트 플랫폼을 이용한 결제 기능을 제공하고 있습니다.
저희 팀은 최근 가장 핵심 시스템이자 오랫동안 운영해 온 결제 시스템의 DB를 Nbase-T에서
Vitess
로 마이그레이션했습니다. 이와 관련해서 앞서
일 평균 30억 건을 처리하는 결제 시스템의 DB를 Vitess로 교체하기 - 1. 솔루션 선정기
라는 글에서 마이그레이션할 다음 솔루션을 선정하기 위해 진행한 PoC 과정과 그 결과 Vitess를 선정한 이유를 소개했는데요. 이번 글에서는 실제로 개발 및 운영 단계에서 Vitess를 어떻게 활용하고 있는지 소개하겠습니다(1편에서 Vitess에 대해 자세히 소개하고 있으므로 1편을 먼저 읽고 오시면 2편을 보다 쉽게 이해하실 수 있습니다).
개발기
애플리케이션 서버에서 Vitess를 사용하려면 먼저 프로토콜을 선택하고 그에 맞춰 개발해야 합니다. 개발기에서는 저희 팀이 현재 어떤 프로토콜을 사용하고 있는지 소개하고, 아울러 Vitess의 MySQL 호환성과 함께 Vitess가 제공하는 다양한 유용한 기능들도 함께 살펴보겠습니다.
gRPC 프로토콜 vs MySQL 프로토콜
Vitess 사용 준비가 완료되어 VTGate에 DB 툴(예: MySQL Workbench)로 접속해 쿼리를 실행할 수 있다면, 이제 애플리케이션 서버에서 어떤 프로토콜을 사용할지 선택할 차례입니다.
VTGate는 MySQL 프로토콜과 gRPC 프로토콜을 지원합니다. 따라서 어떤 프로토콜로 개발할지 선택해야 했는데요. 저희는 과거 NBase-T 샤딩 DB에서 성능이 우수한 RPC 프로토콜을 사용한 경험이 있어서, 먼저 Vitess 공식 Git 리포지터리에서 제공하는 Java 클라이언트(
참고
) 중
grpc-client
모듈을 활용해 개발했습니다.
그러나 개발 후 성능 테스트 과정에서 간헐적으로
http2: frame too large
에러가 발생했고, CPU 사용량 또한 크게 증가하는 모습을 보였습니다. 또한 Vitess에서 제공하는 아래
예제 코드
처럼 쿼리 결과를 Java 객체로 변환하는 과정이 매우 번거롭다는 문제도 있었습니다.
try (Cursor cursor = conn.execute(ctx, "SELECT page, time_created_ns, message FROM messages", null, session)) {
    Row row;
    while ((row = cursor.next()) != null) {
      UnsignedLong page = row.getULong("pMySQLage");
      UnsignedLong timeCreated = row.getULong("time_created_ns");
      byte[] message = row.getBytes("message");
      System.out.format("(%s, %s, %s)\n", page, timeCreated, new String(message));
    }
}
저희는 Vitess 공식 Slack 채널에서 조사한 결과 gRPC 프로토콜 사용 시 CPU 오버헤드가 발생한다는 것을 알게 되었습니다. 또한 어떤 프로토콜을 사용해야 할지 문의한 결과 '현재 Vitess 측에서는 관련 모듈을 활발하게 개발하고 있지 않기 때문에 MySQL 프로토콜을 사용해 개발하는 것을 권장한다'는 답변을 받았습니다. 이에 따라 저희 팀은 MySQL 프로토콜을 활용해 애플리케이션을 개발했습니다.
애플리케이션에서 Vitess를 이용해 데이터를 처리하는 방식
현재 저희 팀이 구성한 키스페이스와 스키마를 공유하고, 이를 바탕으로 실제 애플리케이션에서 요청을 처리하는 과정을 설명하겠습니다.
키스페이스와 스키마
저희 팀은 글로벌 키스페이스(global keyspace)와 서비스 키스페이스(service keyspace), 이렇게 두 개의 키스페이스를 운영하고 있습니다.
먼저 글로벌 키스페이스는 단일 샤드로, 자동 증가하는 샤딩 키 관리 테이블을 생성해서 사용하고 있습니다. 이 테이블에는 사용자 정보와 샤딩 키값이 저장됩니다. 대략적인 스키마와
Vitess 스키마
(이하 VSchema)는 다음과 같습니다.
스키마
VSchema
CREATE TABLE `account_sharding_key` (
    `sharding_key` bigint(20) NOT NULL AUTO_INCREMENT,
    `account_id` varchar(255) NOT NULL,
    PRIMARY KEY (`sharding_key`),
    UNIQUE KEY `pkidx` (`account_id`)
)
{
  "sharded": false,
  "tables": {
    "account_sharding_key": {
      "type": "sequence"
    }
  }
}
다음으로 서비스 키스페이스는 N개의 샤드로 분산해 운영하고 있으며, 가상 재화 서비스를 제공하기 위한 코인 잔액과 코인 충전, 사용 내역 등의 데이터를 저장하는 테이블을 운영하고 있습니다. 서비스 키스페이스는 프라이머리-레플리카-읽기전용(primay-replica-readonly) 혹은 프라이머리-레플리카(primary-replica) 구조 등으로 운영할 수 있습니다.
다음은 저희가 사용하는 사용 내역 테이블의 대략적인 스키마와 VSchema입니다.
Vindex
는 해시를 사용하고 있습니다.
스키마
VSchema
CREATE TABLE `transaction` (
  `sharding_key` bigint(20) NOT NULL,
  `amount` DECIMAL(38,10) NOT NULL,
  ... // 다른 칼럼 생략
)
{
  "sharded": true,
  "vindexes": {
    "hash": {
      "type": "hash"
    }
  },
  "tables": {
    ... // 다른 테이블 생략
    "transaction": {
      "column_vindexes": [
        {
          "column": "sharding_key",
          "name": "hash"
        }
      ]
    }
  }
}
애플리케이션이 Vitess와 작동하는 방식
다음은 애플리케이션에서 코인 충전 요청이 들어왔을 때 애플리케이션과 Vitess의 작동 흐름을 나타낸 것입니다.
위 그림처럼 샤딩 키를 조건절에 넣거나 데이터 삽입(
insert
) 시 샤딩 키를 포함해 삽입하면 VTGate에서 해당 사용자의 데이터가 존재하는 샤드를 특정하며, 이를 통해 해당 샤드에만 쿼리가 수행됩니다.
MySQL과의 호환성
Vitess의 트랜잭션 격리 수준과 쿼리 제약 사항 등 MySQL 호환성에 대해 소개하겠습니다.
트랜잭션 격리 수준
Vitess는 단일 샤드 트랜잭션에서는 MySQL의 트랜잭션 격리 수준(isolation level) 중
REPEATABLE READ
가 적용되며, 다중 샤드 트랜잭션에서는
READ COMMITTED
가 적용됩니다. 클라이언트는
SET
명령을 활용해 트랜잭션 모드를 변경할 수 있습니다.
쿼리 제약 사항
Vitess가 MySQL 프로토콜을 지원하기는 하지만 샤딩 DB 특성에 따라 일부 쿼리에 제약 사항이 존재합니다. 쿼리 제약 사항은 Vitess의 공식 Git 리포지터리의
unsupported_cases.json
에서 관리되고 있습니다.
그 외
Views: 샤딩된 키스페이스에 대해서만 지원하며, VTGate와
VTTablet
실행 시
--enable-views
옵션을 활성화하면 사용할 수 있습니다.
임시 테이블: 샤딩되지 않은 키스페이스에서만 생성할 수 있습니다.
이 글에서 소개한 기능 외에 MySQL 기능 호환 여부는 Vitess에서 공식으로 제공하는
MySQL Compatibility 문서
를 참고하시기 바랍니다.
Vitess가 제공하는 유용한 기능
Vitess가 제공하는 여러 유용한 기능(
참고
) 중에서 현재 저희 팀이 사용하고 있거나 추후 사용을 고려하고 있는 기능들을 소개하겠습니다.
Two-Phase Commit
: 분산된 샤드 간 트랜잭션을 처리할 수 있습니다.
VEXPLAIN
,
VTEXPLAIN
: 쿼리 실행 계획을 분석하는 데 사용합니다. VTEXPLAIN 기능의 경우
VTAdmin
에서 웹 UI로 수행할 수 있기 때문에 저희는 VTAdmin을 이용해 실행 계획을 분석하고 있습니다.
운영기
다음으로 운영 단계에서 Vitess를 어떻게 활용하고 있는지 모니터링 방식과 DB 운영 프로세스, 페일오버(failover) 테스트로 나눠 하나씩 살펴보겠습니다.
모니터링 방식
저희는 현재 주로 VTOrc 지표(metrics)와 VTGate 및 VTTablet 지표, Vitess 로그 등을 모니터링하고 있습니다. 각각을 어떻게 모니터링하고 있는지 소개하겠습니다.
VTOrc 지표 모니터링
VTOrc는 Vitess의 문제를 자동으로 감지하고 및 복구하는 도구입니다. MySQL의 고가용성과 복제를 관리하는 도구인
Orchestrator
를 기반으로 제작됐습니다. VTOrc가 작동하는 흐름은 다음과 같습니다.
VTOrc는 토폴로지 서버와 VTTablet으로부터 데이터를 취합해 문제 발생 여부를 파악합니다. 이때 문제 발생 여부와 발생한 문제 관련 정보는 지표로 수집할 수 있는데요. VTOrc가 현재 16000 포트에서 구동되고 있다면 'http://{host}:16000/metrics'에서 지표를 수집할 수 있습니다. 현재 저희 팀에서는 Promethous를 통해서 VTOrc의 지표를 수집하고 있으며, 문제 발생 시 이메일과 Slack으로 알람을 받고 있습니다.
문제 발생 여부를 확인하는 지표는 다음과 같이 기록됩니다. 문제 상황은
analysis
에 명시되며,
keyspace
와
shard
정보가 기록되고, VTTablet을 실행할 때 부여되는 고유한 값인
tablet_alias
도 기록됩니다. 따라서
tablet_alias
를 이용해 문제가 발생한 VTTablet과 연결된 MySQL 노드를 식별할 수 있습니다.
vtorc_detected_problems{analysis="PrimarySingleReplicaDead",keyspace="global",shard="0",tablet_alias="zone1-0000003000"} 0
vtorc_detected_problems{analysis="ReplicaIsWritable",keyspace="service",shard="0",tablet_alias="zone1-0000003001"} 0
vtorc_detected_problems{analysis="ReplicationStopped",keyspace="service",shard="-80",tablet_alias="zone1-0000001101"} 0
vtorc_detected_problems{analysis="UnreachablePrimary",keyspace="service",shard="-80",tablet_alias="zone1-0000001100"} 0
최근 리커버리가 수행된 내역은 지표 중
vtorc_recoveries_count{}
로 확인할 수 있으며, VTOrc의 웹 페이지에서 확인할 수도 있습니다. 'http://{host}:16000/debug/status'로 접속하면 다음과 같이 복구 내역을 확인할 수 있습니다.
이 글에서 소개한 내용 외에 다른 가시성 높은 지표를 보고 싶다면 'http://{host}:16000/debug/vars'에 접속해서
DetectedProblems
나
RecoveriesCount
등을 참고하시면 됩니다.
VTGate 및 VTTablet 지표 모니터링
앞서 소개한 VTOrc와 동일한
/metrics
경로를 Prometheus로 수집해 VTGate와 VTTablet 등 Vitess 프로그램의 지표를 수집 및 모니터링할 수 있습니다.
다음은 VTGate와 VTTablet에서 수집할 수 있는 지표들입니다. 이를 이용해 각 서비스 성격에 맞게 Grafana 대시보드를 구성하거나 Prometheus와 Grafana에서 제공하는 알람 기능을 활용해 장애 상황을 감지할 수 있습니다.
VTGate
지표
설명
vtgate_api_count
VTGate API counts
vtgate_api_error_counts
VTGate API error counts per error type
vtgate_api_bucket
Histogram data for the VTGate API in Vitess
VTTablet
지표
설명
vttablet_queries_count
vttablet_query_counts
vttablet_query_counts_with_tablet_type
VTTablet query counts
vttablet_errors
Counter that tracks critical errors occurring in VTTablet
vttablet_internal_errors
Counter that tracks the number of internal component errors in VTTablet
vttablet_mysql_bucket
vttablet_queries_bucket
vttablet_results_bucket
Histogram data for VTTablet
Vitess 로그 모니터링
Vitess의 로그는 각 프로그램 수행 시에
--log_dir
로 지정한 장소에 다음과 같이 쌓입니다.
$ ls -all
vtgate.FATAL -> vtgate.hostname.log.FATAL.YYYYMMDD-HHMMSS
vtgate.ERROR -> vtgate.hostname.log.ERROR.YYYYMMDD-HHMMSS 
vtgate.WARNING -> vtgate.hostname.log.WARNING.YYYYMMDD-HHMMSS 
vtgate.INFO -> vtgate.hostname.log.INFO.YYYYMMDD-HHMMSS 
...
vtgate.hostname.log.FATAL.YYYYMMDD-HHMMSS
vtgate.hostname.log.ERROR.YYYYMMDD-HHMMSS
vtgate.hostname.log.WARNING.YYYYMMDD-HHMMSS
vtgate.hostname.log.INFO.YYYYMMDD-HHMMSS
파일로 저장되는 로그를 로깅 시스템으로 전송하기 위해서는
Filebeat
나
Vector
등의 프로그램을 사용해야 하는데요. 저희 팀은 Vector를 통해서
INFO
레벨 이상의 모든 로그를 수집하고 있고,
ERROR
나
FATAL
레벨의 로그가 수집되면 알람을 받고 있습니다.
만약 저희와 같이 Vector를 사용하신다면
VRL(Vector Remap Language)
에 대해서 수행해 볼 수 있는
플레이그라운드
가 제공되고 있으니 문법이나 필터링 로직을 테스트하실 때 사용해 보시길 바랍니다.
그 외 모니터링
아래 표는 앞서 설명한 모니터링 외에 현재 저희 팀에서 추가로 수행하고 있는 모니터링을 정리한 표입니다.
모니터링 종류
설명
MySQL 모니터링
사내 DB에 대해서 Grafana를 이용해 모니터링하고 있으며, MySQL이 다운되거나 일정 시간 이상 복제 지연이 발생하는 등의 각종 문제 상황 발생 시 DBA 조직과 개발팀 모두 알람을 받고 있습니다.
인프라 모니터링
CPU와 메모리, 디스크 등의 인프라 자원을 모니터링하며 관련 알람을 받고 있습니다.
헬스 체크 모니터링
장애를 빠르게 감지하기 위해서 VTGate와 VTTablet,
vtctld
,
etcd
(글로벌 토폴로지 서버)에 대해서 자체 헬스 체크를 구현하여 HTTP 요청 시 정상 응답(200)하는지 확인하고 있습니다. VTGate와 VTTablet, vtctld에는
/debug/status
로
GET
요청을 보내며, etcd 서버에는
/version
에
GET
요청을 보냅니다.
DB 운영 작업 프로세스
Vitess를 도입하면서 DBA와 협업해 수립한 DB 운영 작업 프로세스를 소개합니다.
DDL 수행 프로세스 소개
Vitess에서 스키마를 관리하는 방식은 크게 '비관리 방식(unmagaed)'와 '관리 방식(managed)'으로 나눌 수 있습니다.
비관리 방식: Vitess의 스키마 관리 기능을 사용하지 않고 직접 DB 스키마를 수정하는 방법입니다.
vtctldclient
의
ApplySchema
명령어 활용
VTGate에서 DDL 전략(strategy)을
direct
로 설정해 DDL 수행
개별 MySQL에서 직접 DDL을 수행하고, vtctldclient의
ReloadSchema
명령어를 활용해 변경된 스키마 정보를 Vitess에 반영
관리 방식: Vitess의 스키마 관리 기능(DDL 전략)을 활용해 DB 스키마를 수정하는 방법으로, Vitess에서 제공하는 전략은
Online DDL strategies 문서
에서 확인할 수 있습니다. 이 글에서는 저희가 테스트해 본
vitess
와
mysql
전략을 소개하겠습니다.
vitess
:  Vitess에 내장된
VReplication
메커니즘을 활용하는 방법
mysql
: Vitess의 온라인 DDL 스케줄러가 관리하지만 일반 MySQL 문을 통해 실행하는 방법
저희 측에서는 다음 DDL 목록으로 총 세 가지 방법을 테스트해 봤습니다.
varchar
칼럼 크기 증가 및 감소
칼럼 추가 및 삭제
인덱스 추가
테스트 결과는 다음과 같습니다.
스키마 관리 방식
수행 방식(DDL 전략)
테스트 결과
비관리 방식(unmanaged)
개별 MySQL에서 직접 DDL 수행
단점: 모든 샤드의 프라이머리 노드에서 개별적으로 DDL을 수행해야 합니다.
장점
DBA의 역할이 MySQL DB에 대한 DDL 수행 및 반영 여부 확인으로 한정되기 때문에 Vitess에 대한 이해는 필요하지 않습니다.
기존 DBA 업무와 동일하게 진행할 수 있으며, MySQL에서 온라인 DDL이 불가능한 쿼리(참고)에 대해서 pt-osc 등의 서드 파티 도구를 활용해 애플리케이션에 미치는 영향을 최소화할 수 있습니다.
관리 방식(managed)
vitess
단점: MySQL에서 온라인 DDL을 지원하지 않는 쿼리 수행 시 각 샤드별로 완료될 때마다 순단이 발생하고, 애플리케이션에서 해당 샤드로의 쿼리 요청 시 에러가 발생합니다.
장점
일괄 수행이 가능하며 추적 기능을 제공합니다.
그 외 리버트(revert) 기능과 컷 오버 백오프(cut-over backoff), 강제 컷 오버(forced cut-over) 등의 기능을 제공합니다.
mysql
단점: MySQL에서 온라인 DDL을 지원하지 않는 쿼리 수행 시 각 샤드별로 완료될 때마다 순단이 발생하고, 애플리케이션에서 해당 샤드로의 쿼리 요청 시 에러가 발생합니다.
장점: 일괄 수행이 가능하며 추적 기능을 제공합니다.
테스트 결과 온라인 DDL 지원과 DBA 팀과의 역할과 책임을 구분하기 위해 비관리 방식(개별 MySQL에서 DBA 분이 직접 DDL 수행)을 선택했습니다.
이를 반영해 저희 팀에서 확립한 DDL 수행 프로세스는 다음과 같습니다.
쿼리 작성 및 기안 상신(개발 팀)
MySQL 수준의 DDL을 각 샤드의 프라이머리에서 직접 진행(DBA)
vtctldclient의
ReloadSchema
와
ValidateSchemaKeyspace
명령어를 이용해 Vitess에 스키마 반영 및 샤드 간 스키마 일치 여부 검증(개발 팀)
샤드의 프라이머리 변경(
PlannedReparentShard
명령어 수행 작업)
프라이머리 노드의 MySQL 장비에 대한 점검 작업이 필요할 때 기존 레플리카를 프라이머리로 승격하는 경우가 있습니다. 이때 vtctldclient의
PlannedReparentShard
명령어를 통해 프라이머리 승격이 가능한데요. 프라이머리 승격 시 일시적으로 순단이 발생하고, 애플리케이션에서 에러가 발생합니다.
페일오버 테스트
다음으로 Vitess 운영 중 발생 가능한 여러 장애 상황에서 페일오버 기능이 제대로 작동하는지 확인하기 위해 저희가 실시한 테스트와 결과를 소개하겠습니다.
프라이머리 노드 다운 상황의 페일오버 테스트
샤드의 프라이머리 노드에서 MySQL 프로세스를 종료했을 때 VTOrc가 정상적으로 장애 조치를 수행하는지 테스트해 봤습니다. 다음은 페일오버 테스트 과정을 나타낸 것입니다.
1. MySQL 프라이머리 노드 종료(kill)
2. 애플리케이션 장애 발생
3-4. VTOrc에서 헬스 체크를 통해 장애 감지(에러 코드:
DeadPrimary
)
5-6 새로운 프라이머리 승격(
EmergencyReparentShard
) 작업 수행
7. 애플리케이션 장애 해소
테스트 결과, 애플리케이션에 발생하는 장애는 10초 내외인 것을 확인했습니다. 따라서 프라이머리 노드에 장애가 발생해 노드가 다운되더라도 10초 내외로 자동으로 복구된다는 것을 확인할 수 있었습니다.
페일오버 테스트 중 발생한 GTID 일관성 이슈 및 해결 방법
GTID(global transaction identifier)는 각 트랜잭션에 부여되는 고유한 식별자를 의미합니다. 레플리카 노드에 프라이머리 노드에서 복제되지 않은 트랜잭션이 발생할 경우 이 트랜잭션의 GTID는 프라이머리 노드에는 없기 때문에 이 GTID를 잘못된 GTID(errant GTID)라고 부릅니다. 잘못된 GTID는 주로 복제가 활성화된 상태에서 레플리카 노드에 직접 DML을 수행할 때 발생합니다.
저희 팀은 프라이머리 다운 테스트를 진행하는 도중 잘못된 GTID가 발생하는 상황을 겪었습니다. 새로운 프라이머리 노드를 선언한 후 이전에 종료했던 MySQL을 재구동할 때 발생했으며, VTOrc를 통해
ErrantGTIDDetected
오류가 발생한 것을 확인할 수 있었습니다.
잘못된 GTID가 발생했을 때 복구하는 과정은 다음과 같습니다.
vtctldclient의
DeleteTablets
명령어로 문제가 발생한 노드(
tabletType
이
REPLICA
혹은
RDONLY
)의 VTTablet을 제거합니다.
DeleteTablets
을 실행하면 중앙 데이터 저장소의 VTTablet 관련 메타데이터에서 해당 태블릿 정보가 삭제되며, 정상 제거 여부는 VTAdmin이나 vtctldclient
GetTablets
명령어로 확인할 수 있습니다.
문제가 발생한 노드의 VTTablet 프로세스를 종료합니다.
MySQL의 복제 설정 제거 및 GTID 정합성 발생하기 전의 최신 백업 버전으로 복구(restore)합니다.
VTTablet 프로세스를 재구동(복제 재개)합니다.
프라이머리 다운 테스트 과정에서 GTID 정합성 불일치의 원인은 기존 프라이머리 노드의 VTTablet 프로세스는
tabletType
이
PRIMARY
로 설정돼 있기 때문에 발생했습니다. 테스트 중 문제가 발생했던 MySQL 재구동전에 기존 VTTablet 프로세스를 종료하고 MySQL 재구동 이후 VTTablet의
tabletType
을
PRIMARY
가 아닌
REPLICA
나
RDONLY
(읽기 전용)로 변경해서 재구동한 결과 문제가 발생하지 않았습니다.
그 외 페일오버 테스트 중 발견한 사항 공유
VTTablet 프로세스가 다운되면 VTOrc가 에러(에러 코드:
InvalidPrimary
,
ConnectedToWrongPrimary
)를 감지하지만 페일오버 처리는 되지 않기 때문에 직접 해결해야 합니다.
또한 VTGate에서 제공하는 버퍼링 기능을 활용하면
EmergencyReparentShard
와
PlannedReparentShard
명령어 수행 과정에서 애플리케이션에 미치는 장애 영향을 최소화할 수 있습니다. 그러나 버퍼링 기능 때문에 애플리케이션의 스레드를 점유한 채 대기하는 경우 애플리케이션 서버 자원이 고갈될 수 있기 때문에 적절한 타임아웃을 설정해 사용해야 합니다.
마치며
6개월간 Vitess를 운영해 본 결과 Vitess는 매우 다양한 기능을 제공하는 견고한 플랫폼이었습니다. 그간의 경험을 토대로 저희가 생각해 본 Vitess의 장단점을 간략히 정리해 봤습니다.
장점
Vitess는 문서가 체계적으로 잘 정리돼 있어서 공식 문서만으로도 Vitess를 설치 및 설정하고 애플리케이션을 개발할 수 있습니다.
다만, 설정값 튜닝 작업과 관련해서는 가이드가 보기 쉽게 제공되고 있지 않아서 사용 환경에 따라 다양한 설정값으로 성능 테스트를 진행할 필요가 있습니다.
MySQL 프로토콜을 지원하기 때문에 추가 학습 없이 기존 MySQL 연동 코드를 재사용할 수 있어 개발 시간을 단축할 수 있습니다.
리샤딩과 다양한 샤딩 키 처리 방식을 지원하며, 분산 트랜잭션을 지원하는 등 샤딩 관련 다양한 기능을 제공하고, 이런 기능들을 vtctldclient나 VTAdmin 등을 이용해 쉽게 조작할 수 있습니다.
VTOrc를 통해 장애 감지와 복구 기능을 제공하고, 모든 Vitess 프로그램은 Prometheus 지표 수집이 가능해 모니터링하기 용이합니다.
단점
Vitess를 지속적으로 학습할 필요가 있고, 오픈소스 특성상 버전 업데이트를 추적하고 적용하는 데 부담이 있습니다.
저희는 두 편에 걸쳐 마이그레이션할 다음 솔루션을 선정하기 위해 진행한 PoC 과정과 그 결과 Vitess를 선정한 이유를 소개하고, 실제로 개발 및 운영 단계에서 Vitess를 어떻게 활용하고 있는지 Vitess의 장단점을 포함해 소개했습니다. 이 두 글이 팀과 서비스의 방향에 맞춰 샤딩 솔루션을 선택하려는 분들과 그 결과 Vitess를 도입하고자 고려하고 계신 분들에게 도움이 되기를 바라며 이만 마치겠습니다.
Name:
김영재
Description:
LINE Billing Platform 개발 팀에서 LINE 앱 내 여러 서비스가 이용하는 결제 플랫폼을 개발하고 있습니다.
Name:
이정재
Description:
LINE Billing Platform 개발 팀에서 LINE 앱 내 여러 서비스가 이용하는 결제 플랫폼을 개발하고 있습니다.
Share on Facebook
Share on X
Share on Line
Copy Link
Share on はてなブックマーク
"""

def test_generate_structured_summary_real():
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
        return

    summary = generate_structured_summary(
        article_text=ARTICLE_TEXT,
        openai_api_key=OPENAI_API_KEY
    )

    print("\n=== Openai 요약 결과 ===")
    print(summary)

if __name__ == "__main__":
    test_generate_structured_summary_real()